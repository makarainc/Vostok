# ===========================================================================
# Copyright 2010 Makara, Inc.
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain a
# copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/VPM/Package.py $
# $Date: 2010-04-10 00:29:29 +0200 (Sa, 10 Apr 2010) $
# $Revision: 6599 $

import copy
import fcntl
#import hashlib                         # (2.5 and higher)
import md5
import imp
import os
import glob
import re
import shutil
import stat
import struct
import sys
import tempfile
import urllib
import logging
import zipfile
import xml.dom.minidom
from subprocess import call, Popen, PIPE

from VPM.Constants import *
from VPM.DB import DB, DBError
from VPM.Environment import Environment
from VPM.Lock import LockError, Lock
from VPM.Utils import read_file, write_file


class ControlFileError (ValueError):
    pass

class PackageError (ValueError):
    pass

class HookError (OSError):
    pass


# This is outdated
# Paths tend to get a bit confusing when dealing with (i.e. building,
# packaging, unpackaging, installing, or removing/purging) packages, so here
# is the the nomenclature used throughout the Package class.  The
# single-letter codes are:
#
#   'r' = root
#   'p' = prefix
#   'b' = basename (name w/o extension)
#   'e' = extension
#   'n' = full name (= name w/extension)
#
# Build Hierarchy:
#
#             ../../tmp/build/opt/cartridges/www-static/apache2-2.2.3
#   bld_r__   ---------------
#   bld__p_                   -------------------------
#   bld___n                                             -------------
#   bld_rp_   -----------------------------------------
#   bld__pn                   ---------------------------------------
#   bld_rpn   -------------------------------------------------------
#
# Packaging Hierarchy:
#
#             ../../tmp/tmpXXXXXX/www-static.apache2_2.2.3_1_i386.vpm
#   pkg_r_    -------------------
#   pkg__b                        -------------------------------
#   pkg__e                                                       ----
#   pkg_rb    ---------------------------------------------------
#   pkg__n                        -----------------------------------
#   pkg_rn    -------------------------------------------------------
#
# Destination Hierarchy:
#
#             ../../tmp/www-static.apache2_2.2.3_1_i386.vpm
#   dst_r_    ---------
#   dst__b              -------------------------------
#   dst__e                                             ----
#   dst_rb    -----------------------------------------
#   dst__n              -----------------------------------
#   dst_rn    ---------------------------------------------
#
# Installation Hierarchy:
#
#             ../../tmp/opt/cartridges/www-static/apache2-2.2.3
#   ins_r__   ---------
#   ins__p_             -------------------------
#   ins___n                                       -------------
#   ins_rp_   -----------------------------------
#   ins__pn             ---------------------------------------
#   ins_rpn   -------------------------------------------------
#
# Other Hierarchies are named accordingly.

class Package (object):
    __ACTION_INSTALL = 'install'
    __ACTION_REMOVE = 'remove'
    __ACTION_PURGE = 'purge'

    __locks = None
    __pdb = None

    env = None

    def __init__(self, env):
        if not isinstance(env, Environment):
            raise ValueError("not an Environment instance: '%s'" % env)
        self.__locks = {}
        self.env = env

    #
    # Private Methods

    def db(self):
        if self.__pdb is None:
            self.__pdb = DB(self.env)

        return self.__pdb

    # Utils - - - - - - - - - - - - - - - - -

    def _mktmpd(self, root = None):
        if not isinstance(root, basestring):
            root = self.env.tmp_package_dir
        tempfile.tempdir = root

        if not os.path.exists(root):
            os.makedirs(root)

        d = tempfile.mkdtemp()
        # ensure permissions are 755 -- at least for toplevel archive dirs
        os.chmod(d, 00755)

        return d

    @staticmethod
    def _rm_rf(path):
        if path == '/':
            raise OSError("Aborting rm -rf / call")
        
        cmd = [BIN_RM, '-rf', path]
        rc = call(cmd)

        if rc != 0:
            raise OSError("command '%s' failed with code %d" % \
                          (' '.join(cmd), rc))

    # Return abs paths to all the files in a directory tree.
    # Don't read symlinks or cross mount points.
    @staticmethod
    def _tree_list(path):
        files=[]
        dirs=[path]
        try:
            while True:
                d=dirs.pop()
                ents=os.listdir(d)
                for ent in ents:
                    np=os.path.join(path, ent)
                    if os.path.islink(np):
                        pass
                    elif os.path.ismount(np):
                        pass
                    elif os.path.isdir(np):
                        dirs.append(np)
                    elif os.path.isfile(np):
                        files.append(np)
        except IndexError:
            pass

        return files


    # Copy name from src_root to dst_root, complete with filesystem
    # meta-information.
    @staticmethod
    def _tree_copy(pkg_name, src_root, dst_root, star = None):
        if star is None:
            name = pkg_name
        else:
            name = '.'

        p1 = Popen([BIN_TAR, '-C', src_root, '-cf', '-', name], stdout = PIPE)
        p2 = Popen([BIN_TAR, '-C', dst_root, '-xf', '-'], stdin = p1.stdout)
        rc = p2.wait()

        if rc != 0:
            raise OSError("failed to install package '%s' to '%s': %d" %
                          (pkg_name, dst_root, rc))

    # Move source_tree s__pn rooted at s_r__ to destination root d_r__, complete
    # with filesystem metainformation.  Defers to _tree_copy() if s_r__ and
    # d_r__ reside on different filesystems.
    #
    # BUG: this function will fail if s_r__ and d_r__ reside on the same
    # filesystem and any part of s__pn does already exist.

    @staticmethod
    def _tree_move(s_d, name, d_d):
        if (os.stat(s_d)[stat.ST_DEV] == os.stat(d_d)[stat.ST_DEV]):
            try:
                os.rename(os.path.join(s_d, name), os.path.join(d_d, name))
            except OSError, e:
                raise OSError("failed to copy '%s' from '%s' to '%s': %s" %
                              (name, s_d, d_d, e))
        else:
            _tree_copy(s_d, name, d_d)
            _rm_rf(os.path.join(s_d, name))

    @staticmethod
    def _import_module(name, location):
        f, p, d = imp.find_module(name, [location])

        try:
            module = imp.load_module(name, f, p, d)
        finally:
            if f:
                f.close()

        return module

    def _lock(self, path, mode):
        l = Lock()

        l.acquire(os.path.join(path, VPM_LOCK_FILE_NAME), mode)
        self.__locks[path] = l

        return True

    def _unlock(self, path):        
        if path in self.__locks:
            self.__locks[path].release()
            
            lock_file = os.path.join(path, VPM_LOCK_FILE_NAME)
            if os.path.exists(lock_file):
                self._rm_rf(lock_file)
            
            del self.__locks[path]

    # zipfile.extractall() method only available in python >= 2.6
    @staticmethod
    def _extract_archive(archive, inst_root, gz = False):
        cmd = [BIN_UNZIP, '-qq', archive, '-d', inst_root]
        rc = call(cmd)

        if rc != 0:
            raise OSError("'%s' failed to extract with code %d" % \
                          (' '.join(cmd), rc))

    def _validate_package(self, package):
        if not package:
            raise ValueError("'%s' is not a package pathname" % package)

        if not os.path.isfile(package):
            raise ValueError("'%s' is not a file" % package)

        if not zipfile.is_zipfile(package):
            raise PackageError("'%s' is not a package archive" % package)

        dummy, pkg__e = os.path.splitext(package)

        if not pkg__e == '.' + VPM_PKG_EXTENSION:
            raise ValueError("'%s' is not a package file" % package)

        return True


    # Control Information - - - - - - - - - -

    # Control information is constructed
    #
    # Construct from Package (unpack, install, installable)
    #   info/control               load                         cinfo
    #   info/changelog             load if exists | default     binfo
    #   -                          determine                    iinfo
    #
    # Construct from Package Tree (pack, install, installable)
    #   info/control               load                         cinfo
    #   info/changelog             load if exists | default     binfo
    #   -                          (passed in)                  iinfo
    #
    # Construct from self.env.lib_dir/packages/name.* (install/remove)
    #   name.control               load                         cinfo
    #   name.build                 load                         binfo
    #   name.location              load                         iinfo
    #
    #
    # Store in Package (pack)
    #   cinfo                      store       info/control
    #   binfo                      store       info/changelog
    #   iinfo                      -           -
    #
    # Store in Tree (unpack, install)
    #   cinfo                      store       info/control
    #   binfo                      store       info/changelog
    #   iinfo                      -           -
    #
    # Store in LIBDIR/packages/name.* (install/remove)
    #   cinfo                      store       name.control
    #   binfo                      store       name.build
    #   iinfo                      store       name.location

    @staticmethod
    def _parse_declarations(lines, pathname):
        d = {}
        k = None
        n = 0

        if isinstance(lines, basestring):
            lines = [lines]

        for l in lines:
            n += 1
            m = re.match('^(?:\s*#.*)?$', l)

            if m:
                pass        # ignore empty or comment lines
            else:
                m = re.match('^\s+(.*?)\s*$', l)
                if m and k is not None:
                    t = m.group(1)

                    if re.match('^.*\S$', d[k]): # join with whitespace
                        t = ' ' + t

                    d[k] += t
                else:
                    m = re.match('^(?P<key>\S+):\s*(?P<value>.*?)\s*$', l)
                    if m:
                        k = m.group('key')
                        v = m.group('value')

                        m = re.match('^\s*\$Rev:\s*(?P<rev>\d+)\s*\$\s*$', v)
                        if m:
                            v = m.group('rev')

                        d[k] = v
                    else:
                        raise ControlFileError("%s: line %d malformed: '%s'" \
                                               % (pathname, n, l))

        return d

    @staticmethod
    def _parse_settings_mapping(path):
        mapping = {}

        data = read_file(path)
        if data is None:
            return None

        lines = data.splitlines()

        for line in lines:
            k, v = line.strip().split("\t")

            mapping[k.strip()] = v.strip()

        return mapping

    # FIXME this can be refactored better
    def _load_control_info_from_archive(self, archive, cfile):
        cdata = archive.read(cfile)
        cinfo = self._parse_declarations(cdata.splitlines(), cfile)

        return cinfo

    def _load_build_info_from_archive(self, archive, bfile):
        binfo = None

        if bfile:
            bstat = archive.getinfo(bfile)

            if bstat:
                bdata = archive.read(bfile)
                binfo = self._parse_declarations(bdata.splitlines(), bfile)

        if binfo is None:
            binfo = {KEY_BUIL: VAL_BUIL_DEFAULT}

        return binfo

    def _load_control_info_from_tree(self, cfile):
        cdata = read_file(cfile, True)
        cinfo = self._parse_declarations(cdata.splitlines(), cfile)

        return cinfo

    def _load_build_info_from_tree(self, bfile, error = True):
        binfo = None

        if bfile:
            bdata = read_file(bfile, error)

            binfo = self._parse_declarations(bdata.splitlines(), bfile)
        else:
            binfo = {KEY_BUIL: VAL_BUIL_DEFAULT}

        return binfo

    def _load_from_db_aux(self, name, ext):
        f = name + '.' + ext
        d = self.__pdb.read_package_file(f)
        i = self._parse_declarations(d.splitlines(), f)

        return i

    def _load_control_info_from_db(self, name):
        return self._load_from_db_aux(name, CONTROL_FILE_NAME)

    def _load_build_info_from_db(self, name):
        return self._load_from_db_aux(name, BUILD_FILE_NAME)

    def _load_location_info_from_db(self, name):
        return self._load_from_db_aux(name, LOCATION_FILE_NAME)


    @staticmethod
    def _validate_fields(hash, required, optional, pathname):
        for k in required:
            if k not in hash:
                raise ControlFileError("%s: missing required field '%s'" %
                                       (pathname, k))
            if not hash[k]:
                if k not in frozenset([KEY_INSN]): # may be empty
                    raise ControlFileError("%s: missing value for required "
                                           "field '%s'" % (pathname, k))

        for k in hash.keys():
            if k not in required and k not in optional:
                raise ControlFileError("%s: unknown field '%s'" %
                                       (pathname, k))

    @staticmethod
    def _safe_quote(string):
        # Note: all strings are required to be UTF-8, so we don't encode here
        s = urllib.quote(string, '')

        # urllib.quote doesn't quote '_' which is special to us
        s = re.sub('_', '%5F', s)

        return s

    # There is nothing "safe" about this one--just making the name symmetric
    # to "_safe_quote".
    @staticmethod
    def _safe_unquote(string):
        return urllib.unquote(string)

    # "provides" is parsed according to this grammar:
    #
    #   list    := [{expr{, expr}*}?]
    #   expr    := [token{'\s*(\s*' version '\s*)\s*'}?]
    #   token   := '\w[-+.:\w]*'
    #   version := '[-+.:\w]+'
    #
    # Example:
    #
    #   Name: www-static.apache2
    #   Version: 2.2.3-1
    #   Provides: www-static
    #
    #   The structure is initialized with the expression constructed from
    #   the 'Name' and 'Version' fields, then the 'Provides' line is parsed
    #   and its expressions appended.
    #
    #   => [{'Name'    : 'www-static.apache2',
    #        'Version' : '2.2.3',
    #        'String'  : 'www-static.apache2 (2.2.3)'},
    #       {'Name'    : 'www-static',
    #        'Version' : None,
    #        'String'  : 'www-static.apache2'}]
    #
    @staticmethod
    def _canonicalize_provides(name, version, string, file):
        res = [{KEY_NAME : name,
                KEY_VERS : version,
                KEY_STR  : name + ' (' + version + ')'}]

        if string is not None and not re.match('^\s*$', string):
            seq = re.split('\s*,\s*', string)

            for s in seq:
                m = re.match('^\s*' +
                             '(?P<name>\w[-+.:\w]*)' +
                             '(?:\s*\(\s*' +
                             '(?P<version>\S*)' +
                             '\s*\)\s*)?$',
                             s)

                if not m:
                    raise ControlFileError("%s: bad tag '%s' in '%s'" % \
                                           (file, s, string))
                else:
                    n = m.group('name')
                    v = m.group('version') or version

                    val = {KEY_NAME : n,
                                KEY_VERS : v,
                                KEY_STR  : n + (v and ' (' + v + ')' or '')}
                    if val not in res:
                        res.append(val)

        return res

    @staticmethod
    def _provides2str(exprs, name):
        conj = []

        for e in exprs:
            # FIXME the 'Name' and 'Version' dictionary keys should be
            # really KEY_NQUO and KEY_VQUO since their respective values
            # must be quoted.
            if e[KEY_NAME] is not name: # omit name (provided automatically)
                conj.append(e[KEY_STR])

        return ', '.join(conj)



    # "Depends", and "Conflicts" are parsed according to
    # this grammar which is basically lifted from Debian (except the
    # operators are pythonic and we don't allow "${}" stuff):
    #
    #   list    := [{clause{, clause}*}?]
    #   clause  := [expr{ '\s*|\s*' expr}*]
    #   expr    := [token{'\s*(\s*' op '\s+' version '\s*)\s*'}?]
    #   token   := '\w[-+.:\w]*'
    #   op      := {'<' | '<=' | '==' | '>=' | '>'}
    #   version := '[-+.:\w]+'
    #
    # Example:
    #
    #   'mysql (>= 5), apache | lighttpd (>= 1.5)'
    #
    # is normalized to a logical tree structure:
    #
    #   seq(or(expr('mysql', '(>= 5)')),
    #       or(expr('apache'),
    #          expr('lighttpd', '(>= 1.5)')))
    #
    # and represented in Python as:
    #
    #   [[{'Name'      : 'mysql',
    #      'Predicate' : lambda v: v >= '5.1',
    #      'String'    : 'mysql (>= 5)'}],
    #    [{'Name'      : 'apache2',
    #      'Predicate' : None,
    #      'String'    : 'apache2'},
    #     {'Name'      : 'lighttpd',
    #      'Predicate' : lambda v: v >= '1.5',
    #      'String'    : 'lighttpd (>= 1.5)'}]]
    #
    @staticmethod
    def _canonicalize_relation(string, file):
        res = None

        if string is not None and not re.match('^\s*$', string):
            seq = re.split('\s*,\s*', string)

            for i, s in enumerate(seq):
                exp = seq[i] = re.split('\s*\|\s*', s)

                for j, e in enumerate(exp):
                    m = re.match('^\s*' +
                                 '(?P<name>\w[-+.:\w]*)' +
                                 '(?:\s*\(\s*' +
                                 '(?P<op><|<=|==|>=|>)' +
                                 '\s*' +
                                 '(?P<version>[-+.:\w]+)' +
                                 '\s*\)\s*)?$',
                                 e)

                    if not m:
                        raise ControlFileError("%s: bad tag '%s' in '%s'" % \
                                               (file, e, string))
                    else:
                        n = m.group('name')
                        o = m.group('op') or None
                        v = m.group('version') or None
                        p = o and ("lambda v: v %s '%s'" % (o, v)) or None
                        t = o and ' (%s %s)' % (o, v) or ''

                        exp[j] = {KEY_NAME : n,
                                  KEY_PRED : p,
                                  KEY_STR  : n + t}

            res = seq

        return res

    @staticmethod
    def _relation2str(exprs):
        conj = []

        for cj in exprs:
            disj = []

            for dj in cj:
                disj.append(dj[KEY_STR])

            conj.append(' | '.join(disj))

        return ', '.join(conj)



    def _process_control_info(self, cinfo, cfile):
        self._validate_fields(cinfo, CKEYS_REQ, CKEYS_OPT, cfile)

        # OK, now merge with default info so we can move on
        for k, v in CINFO_DEFAULT.iteritems():
            cinfo.setdefault(k, v)

        # add quoted versions of the user-controlled name and version keys
        cinfo[KEY_NQUO] = self._safe_quote(cinfo[KEY_NAME])
        cinfo[KEY_VQUO] = self._safe_quote(cinfo[KEY_VERS])

        # ensure arch has a known value
        if cinfo[KEY_ARCH] not in VALS_ARCH:
            raise ControlFileError("%s: unknown architecture '%s'" %
                                   (cfile, cinfo[KEY_ARCH]))

        if cinfo[KEY_TYPE] not in VALS_TYPE:
            raise ControlFileError("%s: unkonw package type '%s'" %
                                   (cfile, cinfo[KEY_TYPE]))

        # canonicalize optional values
        prov = KEY_PROV in cinfo and cinfo[KEY_PROV] or None
        cinfo[KEY_PROV] = self._canonicalize_provides(cinfo[KEY_NQUO],
                                                      cinfo[KEY_VQUO],
                                                      prov,
                                                      cfile)
        
        # FIXME: maybe ensure package doesn't depend on or conflict with itself
        for key in (KEY_DEPS, KEY_CONF):
            if key in cinfo:
                cinfo[key] = self._canonicalize_relation(cinfo[key], cfile)
            else:
                cinfo[key] = None

        if not KEY_DESC in cinfo:
            cinfo[KEY_DESC] = None

        return cinfo

    def _process_build_info(self, binfo, bfile):
        self._validate_fields(binfo, BKEYS_REQ, BKEYS_OPT, bfile)

        return binfo

    def _process_location_info(self, linfo, lfile):
        self._validate_fields(linfo, LKEYS_REQ, LKEYS_OPT, lfile)

        return linfo

    def _load_info_from_archive(self, archive):
        '''
        Load control and build file information from an archive
        @param archive: archive pathname
        '''
        archive = zipfile.ZipFile(archive, mode = 'r')
        cfile = os.path.join(META_DIR_NAME, CONTROL_FILE_NAME)
        bfile = os.path.join(META_DIR_NAME, BUILD_FILE_NAME)

        cinfo = self._load_control_info_from_archive(archive, cfile)
        binfo = self._load_build_info_from_archive(archive, bfile)

        self._process_control_info(cinfo, cfile)

        info = cinfo
        info.update(binfo)

        info[KEY_INSR] = ''
        info[KEY_INSN] = info[KEY_NAME]
        info[KEY_PSTATE] = PSTATE_VIRGIN

        return info

    def _load_info_from_tree(self, file_root):
        '''
        Load control and build file information from unpacked
        @param file_root: Path to files
        '''
        cfile = os.path.join(file_root, META_DIR_NAME, CONTROL_FILE_NAME)
        bfile = os.path.join(file_root, META_DIR_NAME, BUILD_FILE_NAME)

        cinfo = self._load_control_info_from_tree(cfile)
        binfo = None

        self._process_control_info(cinfo, cfile)

        if os.path.exists(bfile):
            binfo = self._load_build_info_from_tree(bfile)
            self._process_build_info(binfo, bfile)
        else:
            binfo = self._load_build_info_from_tree(None)

        info = cinfo
        info.update(binfo)

        info[KEY_INSR] = ''
        info[KEY_INSN] = info[KEY_NAME]
        info[KEY_PSTATE] = PSTATE_VIRGIN

        return info

    def _load_info_from_files(self, cfile, bfile):
        cinfo = self._load_control_info_from_tree(cfile)
        binfo = self._load_build_info_from_tree(bfile)

        self._process_control_info(cinfo, cfile)
        self._process_build_info(binfo, bfile)

        info = cinfo
        info.update(binfo)

        return info

    def _load_info_from_db(self, name):
#        cinfo = self._load_control_info_from_db(name)
#        binfo = self._load_build_info_from_db(name)
#        linfo = self._load_location_info_from_db(name)
#
#        self._process_control_info(cinfo, CONTROL_FILE_NAME)
#        self._process_build_info(binfo, BUILD_FILE_NAME)
#        self._process_location_info(linfo, LOCATION_FILE_NAME)
#
#        info = cinfo
#        info.update(binfo)
#        info.update(linfo)
        info = self.db().lookup(name)

        return info


    # Packing/Unpacking - - - - - - - - - - -

    @staticmethod
    def _make_package_name(info):
        return info[KEY_NQUO] + '_' + \
               info[KEY_VQUO] + '-' + \
               info[KEY_BUIL] + '_' + \
               info[KEY_ARCH]

    @staticmethod
    def _sign(car_rpn):                 # FIXME: implement
        return 'VOSTOK GREAT SEAL OF APPROVAL' + "\n"

    @staticmethod
    def _signature_ok(sig, car_rpn):    # FIXME: implement
        return sig == 'VOSTOK GREAT SEAL OF APPROVAL'

    @staticmethod
    def _version_supported(vrs):
        return vrs in VPM_VERSIONS_SUPPORTED

    @staticmethod
    def _write_checksums_file(pkg_rb, checksums):
        write_file(os.path.join(pkg_rb, CHECKSUM_FILE_NAME), checksums)

#    @staticmethod
#    def _write_filelist_file(pkg_rb, filelist):
#        write_file(os.path.join(pkg_rb, META_DIR_NAME, FILELIST_FILE_NAME), filelist)

    @staticmethod
    def _write_version_file(pkg_rb, version):
        write_file(os.path.join(pkg_rb, VERSION_FILE_NAME), version)

    @staticmethod
    def _write_signature_file(pkg_rb, signature):
        write_file(os.path.join(pkg_rb, SIGNATURE_FILE_NAME), signature)

    @staticmethod
    def _write_default_build_file(pathname):
        data = BUILD_FORMAT % (KEY_BUIL, VAL_BUIL_DEFAULT)

        return write_file(pathname, data)

    @staticmethod
    def _read_version_file(pkg_rb):
        return read_file(os.path.join(pkg_rb, VERSION_FILE_NAME))

    @staticmethod
    def _read_signature_file(pkg_rb):
        return read_file(os.path.join(pkg_rb, SIGNATURE_FILE_NAME))

    @staticmethod
    def _verify_zip_safe_to_extract():
        # FIXME: ensure archive does not use paths to other locations
        return True

    def _unpack_package(self, package, pkg_r_):
        self._verify_zip_safe_to_extract()
        self._extract_archive(package, pkg_r_)

    @staticmethod
    def _checksum_content(filelist, car_ext):
        owd = os.getcwd()
        sums = ''

        os.chdir(car_ext)
        try:
            for p in filelist:
                if os.path.isfile(p):
                    # h = hashlib.md5()	# 2.5
                    h = md5.new()

                    f = open(p, 'r')
                    try:
                        h.update(f.read())
                        sums += "%s %s\n" % (h.hexdigest(), p)
                    finally:
                        f.close()
        finally:
            os.chdir(owd)

        return sums

    def _verify_version(self, package, pkg_rb):
        '''
        Verify package version
        @param package: VPM Filename
        @param pkg_rb: Path to (unpacked) package folder
        '''
        vrs = self._read_version_file(pkg_rb)

        if not vrs:
            raise PackageError("'%s': no version information" % package)

        m = re.match('^\s*(\d+(?:\.\d+)*)\s$', vrs)
        if m:
            vrs = m.group(1)
        else:
            raise PackageError("'%s': unrecognized package version '%s'" % \
                               (package, vrs))

        if not self._version_supported(vrs):
            raise PackageError("'%s': unsupported package version '%s'" % \
                               (package, vrs))

    def _verify_signature(self, package, car_rpn):
        '''
        Verify package signature
        @param package: VPM Filename
        @param pkg_rb: Path to (unpacked) package folder
        @param car_rpn: Path to package info folder
        '''
        sig = self._read_signature_file(car_rpn)

        if not sig:
            raise PackageError("'%s': no signature" % package)

        sig = sig.strip()

        if not self._signature_ok(sig, car_rpn):
            raise PackageError("'%s': signature check failure." % package)

    @staticmethod
    def _pack_package(build_root, package_name, destination_root):
        tmpname = package_name + '.zip'
        name = package_name + '.' + VPM_PKG_EXTENSION

        tmpoutput = os.path.join(destination_root , tmpname)
        output = os.path.join(destination_root , name)

        if os.path.exists(output):
            os.remove(output)

        ok = False

        try:
            owd = os.getcwd()

            os.chdir(build_root)

            cmd = [BIN_ZIP, '-q', '-9', '-r', '-y', tmpoutput,
                   '.', '-x', '.vpm.lock', '.svn', 'CVS', '.DS_Store']

            cmd.extend(ZIP_EXCLUDE)

            p = Popen(cmd, stdout = PIPE, stderr = PIPE)
            (out, err) = p.communicate()
            rc = p.returncode

            if rc != 0:
                raise OSError("'%s' failed to pack with code %d" % \
                              (' '.join(cmd), rc))
            elif os.path.exists(tmpoutput):
                os.rename(tmpoutput, output)
                ok = True
        finally:
            os.chdir(owd)
            if not ok and os.path.exists(output):
                os.remove(output)


    def _pack(self, build_root, dest_root):
        '''
        Pack folder tree and write VPM package file
        @param build_root: Build root
        @param dest_root: Destination root
        '''

        res = None
        pkg_name = None

        if not os.path.isdir(dest_root):
            raise IOError("destination must be a directory: '%s'" % dest_root)

        try:
            info = self._load_info_from_tree(build_root)
        except (ControlFileError, IOError), e:
            raise PackageError(e)

        try:
            pkg_name = self._make_package_name(info)

            pkg_info_dir = os.path.join(build_root, META_DIR_NAME)

            bfile = os.path.join(pkg_info_dir, BUILD_FILE_NAME)
            sig = None

            if not os.path.exists(bfile):
                self._write_default_build_file(bfile)

            self._write_version_file(pkg_info_dir, VPM_VERSION + "\n")

            #Build checksums file
            dummy, checksums = self._generate_checksums(build_root)
            self._write_checksums_file(pkg_info_dir, checksums)

            sig = self._sign(build_root)
            # FIXME disabled as per 2614 until we have implemented this
            # self._write_signature_file(pkg_info_dir, sig)

            self._pack_package(build_root, pkg_name, dest_root)
            res = True
            pkg_name = pkg_name + '.' + VPM_PKG_EXTENSION
        except Exception, e:
            raise PackageError(e)

        return res, pkg_name


    def _unpack(self, package):
        '''
        Extract VPM package file
        @param package: VPM Filename
        '''
        pkg_tmp_root = self._mktmpd()

        car_infodir = os.path.join(pkg_tmp_root, META_DIR_NAME)

        self._unpack_package(package, pkg_tmp_root)
        try:
            self._verify_version(package, car_infodir)
            #TODO: verfify checksums list

            # FIXME disabled as per 2614 until we have implemented this
            #self._verify_signature(package, car_infodir)

        except Exception:
            self._rm_rf(pkg_tmp_root)
            raise

        return pkg_tmp_root

    def _cleanup(self, root):
        self._rm_rf(root)


    # Installation/Removal- - - - - - - - - -
    def _set_default_hook_env(self, pkg_root):
        bundle_root = os.path.join(pkg_root, BUNDLE_DIR_NAME)

        hook_env = {}
        for dir in DATA_DIRS:
            key = 'VS_' + dir.upper()
            hook_env[key] = os.path.join(bundle_root, DOT_DATA_DIR_NAME, dir)

        hook_env['VS_HOME'] = bundle_root

        return hook_env

    def _run_hook(self, cmd, env = None):
        '''
        Run a hook.

        @param cmd: The hook to run
        @param env: Environment variables to set before execution
        '''
        if not self.env.no_hooks:
            if not cmd:
                return
            else:
                f = None

                if isinstance(cmd, list):
                    f = cmd[0]
                else:
                    f = cmd

                if os.path.exists(f):
                    e = None
                    p = None
                    r = None

                    if env:
                        e = os.environ.copy() # use fresh copy every time

                        e.update(env)
                    if self.env.trace_hooks:
                        sys.stderr.write("[Package.run_hook]\n"
                                         "  hook   : %s\n" % cmd)
                        if env:
                            # we are not interested in the whole, just env
                            sys.stderr.write("  env    : %s\n" % env)
                    try:
                        out = None
                        err = None

                        if env:
                            p = Popen(cmd, env = e,
                                      stdout = PIPE, stderr = PIPE)
                        else:
                            p = Popen(cmd,
                                      stdout = PIPE, stderr = PIPE)
                        (out, err) = p.communicate()
                        r = p.returncode

                        if self.env.trace_hooks:
                            if out:
                                sys.stderr.write("  stdout : %s\n" % out)
                            if err:
                                sys.stderr.write("  stderr : %s\n" % err)
                    except Exception, e:
                        raise HookError(("'%s': %s\n"
                                         "  stdout: %s\n"
                                         "stderr: %s") % (cmd, e, out, err))
                    if r != 0:
                        raise HookError(("'%s' failed with code %d\n"
                                         "  stdout: %s\n"
                                         "  stderr: %s") % (cmd, r, out, err))

                    return out, err, r

    def _cfg_cartridges_aux(self, action, info, owner, path = None):
        '''
        Cartridge configuration helper
        '''
        #package install root
        root = info[KEY_INSR] or self.env.install_root

        #package install path
        crt_install_path = os.path.join(root, info[KEY_INSN])

        #configure file
        crt_config_file = os.path.join(crt_install_path,
                                       META_DIR_NAME,
                                       CFG_FILE_NAME)
        res = None

        if os.path.exists(crt_config_file):
            m = self._import_module(CFG_BASENAME,
                                    os.path.join(crt_install_path,
                                                 META_DIR_NAME,
                                                 CFG_DIR_NAME))
            p = os.path.join(crt_install_path,
                             META_DIR_NAME, HOOK_DIR_NAME, RELOAD_NAME)

            # FIXME: find a way to use CFG_CLASS_NAME
            cfg = m.Configuration(crt_install_path)

            # FIXME: cartridge install/remove methods should report on errors
            # and return proper reload/restart hooks.  Right now we fake it.
            if action is Package.__ACTION_INSTALL:
                s = None
                d = None

                if os.path.isfile(path):
                    s = path
                elif os.path.isdir(path):
                    l = os.listdir(path)

                    if SETTINGS_FILE_NAME in l:
                        s = os.path.join(path, SETTINGS_FILE_NAME)
                        l.remove(SETTINGS_FILE_NAME)

                    d = map(lambda x: os.path.join(path, x), l)
                else:
                    pass                # FIXME might want to warn about this

                if self.env.trace_hooks:
                    sys.stderr.write(("[Package.cfg_cartridge] configuring "
                                      "%s\n"
                                      "  owner    : %s\n"
                                      "  settings : %s\n"
                                      "  files    : %s\n") % \
                                     (info[KEY_NAME], owner, s, d))
                cfg.install(owner, s, d)
            elif action is Package.__ACTION_REMOVE:
                if self.env.trace_hooks:
                    sys.stderr.write(("[Package.cfg_cartridge] disfiguring "
                                      "%s\n"
                                      "  owner    : %s\n") % \
                                     (info[KEY_NAME], owner))
                cfg.remove(owner)

            if os.path.exists(p):       # may not exist (e.g. php)
                res = p
        else:
            pass                        # FIXME might want to warn about this

        return res

    def _convert_version_string(self, provider, version):
        m = re.match('^\s*(?P<name>\w[-+.:\w]*)(?:\s*\(\s*'
                     + '(?P<op><|<=|==|>=|>)\s*(?P<version>[-+.:\w]+)'
                     + '\s*\)\s*)?$',
                     version)

        op = m.group('op')
        ver = m.group('version')

        if op is not None and ver is not None:
            #translate op
            if op == '<':
                op = 'lt'
            elif op == '<=':
                op = 'le'
            elif op == '==':
                op = 'eq'
            elif op == '>=':
                op = 'ge'
            elif op == '>':
                op = 'gt'

            str = '%s_%s_%s' % (self._safe_quote(provider), op, ver)
        else:
            str = self._safe_quote(provider)

        return str

    def _interpolate_vshome(self, pkg_root, provider, settings_dir):
        #create tmp directory t, copy p over to tmp directory t
        tmp_settings = self._mktmpd()

        self._tree_copy(provider, settings_dir, tmp_settings, True)

        files = self._tree_list(tmp_settings)
        #run replace operation on any file in t

        pattern = re.compile('(@VS_HOME|@\{VS_HOME\}|@\{.*:VS_HOME\})',
                              re.UNICODE & re.MULTILINE)

        vs_home = os.path.join(pkg_root, BUNDLE_DIR_NAME)

        for filename in files:
            filedata = read_file(filename)

            #replace variables with bundle_root
            filedata = re.sub(pattern, vs_home, filedata)

            write_file(filename, filedata)

        return tmp_settings


    def _cfg_cartridges_hook(self, pkg_root, pkg_name, settings, mode = None):
        hook_root = os.path.join(pkg_root, META_DIR_NAME, HOOK_DIR_NAME)

        #FIXME: really process info hook return values
        # query info hook for configure parameters
        #cmd = os.path.join(hook_root, INFO_NAME)
        #out, = self._run_hook([cmd, 'configure'])

        #params = out.split('\t')

        # use returned parameters to call configure hook
        # pass settings file to configure hook
        # FIXME: introduce proper constant
        if mode is None or mode is 'configure':
            hook = os.path.join(hook_root, CONFIGURE_NAME)
            cmd = [hook, pkg_name, settings]
        else:
            hook = os.path.join(hook_root, DECONFIGURE_NAME)
            cmd = [hook, pkg_name]

        #FIXME: substitute variables

        conf_h_env = self._set_default_hook_env(pkg_root)

        self._run_hook(cmd, conf_h_env)


    def _settings_resolve_mapping(self, settings_root, version, feature):
        # parse mapping file:
        mapping = self._parse_settings_mapping(os.path.join(settings_root, 
                SETTINGS_MAP_NAME))
        
        if mapping is not None:
            mapped = None
            
            # find version information from dependency info
            mapped = mapping.get(version, None)
            
            if mapped is not None:
                str = self._safe_quote(mapped)
            else:
                str = self._convert_version_string(feature, 
                    version)
        else:
            str = self._safe_quote(feature)
            
        return str

    def _cfg_cartridges(self, action, info, pkg_root):
        settings_root = os.path.join(pkg_root, META_DIR_NAME, SETTINGS_DIR_NAME)

        name = info[KEY_NAME]

        if info[KEY_DEPS]:
            # Load package dependency table information

            dt = self.db().get_dependency_table_info(name)
            if dt is None:
                return None

            for pkg in dt:
                if action is Package.__ACTION_INSTALL:
                    feature = pkg[KEY_DT_PROV][KEY_DT_PROV_SF]
                    provider = pkg[KEY_DT_PROV][KEY_NAME]

                    provider_info = self.db().lookup(provider)
                    if provider_info[KEY_STAT] is DB.COMMITTED or DB.RESOLVED:
                        version = pkg[KEY_DT_PROV][KEY_VERS]
                        str = self._settings_resolve_mapping(settings_root, version, feature)

                        p = os.path.join(settings_root, str)

                        if os.path.exists(p):
                            #clone settings directory
                            tmp_settings = self._interpolate_vshome(pkg_root,
                                                                    feature,
                                                                    p)

                            #FIXME: use info hook
                            cfg_path = os.path.join(provider_info[KEY_INSR], provider_info[KEY_INSN])

                            try:
                                self._cfg_cartridges_hook(cfg_path, name, tmp_settings, 'configure')
                            finally:
                                # remove temporary directory
                                self._rm_rf(tmp_settings)

                elif action is Package.__ACTION_REMOVE:
                    if pkg[KEY_DT_PROV]:
                        provider = pkg[KEY_DT_PROV][KEY_NAME]
                        provider_info = self.db().lookup(provider, None)
                        
                        cfg_path = os.path.join(provider_info[KEY_INSR], provider_info[KEY_INSN])
                        self._cfg_cartridges_hook(cfg_path, name, None, 'deconfigure')

    def resolve_package_chain(self, info, package):        
        # If not resolved, try to resolve package
        # (i.e. configure it) Lookup complete dependency chain,
        # and check for each package if it is resolved
        chain = []
        try:
            chain = self.db().lookup_dependency_chain(package)
        except DBError, e:
            #print ('Warning: %s' % e)
            return None
        
        chain.reverse()     # walk in reverse order

        # append to make sure the app is configured too
        chain.append(info)
        
        for pkginfo in chain:
            if pkginfo[KEY_STAT] is DB.RESOLVED:
                continue
            elif pkginfo[KEY_STAT] is DB.COMMITTED:
                # check if pkginfo dependencies are met
                ci_r, ci_e = self.db().check_install(pkginfo)
                if not ci_r:
                    raise PackageError(("Package %s can not be "
                                        "configured due to "
                                        "missing dependencies: %s"
                                        % (pkginfo[KEY_NAME], ci_e)))

                # recalculate dependency table                
                self.db().calculate_dependency_table()

                try:
                    pkg_path = os.path.join(pkginfo[KEY_INSR],
                                            pkginfo[KEY_INSN])
                    self._configure_cartridges(pkginfo, pkg_path)
                except Exception, cc_e:
                    raise PackageError(("Package %s can not be configured: %s"
                                        % (pkginfo[KEY_NAME], cc_e)))
            else:
                # If package dependency can not be resolved, error
                raise PackageError("Broken package in dependency chain")
                            
    def _configure_cartridges(self, info, dst_root, deploy_mode = None):
        '''
        Configure packages
        @param info:
        @param dst_root:
        @param deploy_mode:
        '''
        # FIXME: pass selected cartridges
        self._cfg_cartridges(Package.__ACTION_INSTALL, info, dst_root)

        self.db().set_package_state(info, DB.RESOLVED)

    def _deconfigure_cartridges(self, info, dst_root):
        return self._cfg_cartridges(Package.__ACTION_REMOVE, info, dst_root)

    @staticmethod
    def _remove_files(root, filelist):
        owd = os.getcwd()
        if os.path.exists(root):
            os.chdir(root)
            try:
                # FIXME:
                # This doesn't work at all right now.
                # Issues are:
                #   - some files leave .pyc's behind
                #   - app may create data
                for entry in sorted(filelist, reverse = True):
                    try:
                        if re.search('/$', entry):
                            if os.path.exists(entry): # might have already rm'ed
                                for f in os.listdir(entry):
                                    #m = re.search('\.pyc$', f)

                                    #if m:
                                    os.remove(os.path.join(entry, f))
                                os.removedirs(entry)
                        else:
                            if os.path.exists(entry):
                                os.remove(entry)
                    except OSError, e:
                        raise OSError("failed to remove '%s': %s" % (entry, e))
            finally:
                os.chdir(owd)

    def _generate_checksums(self, pkg_install_path):
        p1 = Popen([BIN_TAR, '-C', pkg_install_path, '-cf', '-', '.']
                         , stdout = PIPE)
        p2 = Popen([BIN_TAR, '-tf', '-']
                         , stdin = p1.stdout, stdout = PIPE)
        members = p2.communicate()[0].split('\n')

        members.remove('')              # remove garbage from split
        members.remove('./')              # KLUDGE: don't include degenerate
        if './.vpm.lock' in members:
            members.remove('./.vpm.lock')

        chksums = self._checksum_content(members, pkg_install_path)

        return members, chksums

    # Deprecated
    def _update_filelist_and_checksums(self, pkg_install_path):
        members, chksums = self._generate_checksums(pkg_install_path)

        self._write_filelist_file(pkg_install_path, "\n".join(members))
        self._write_checksums_file(pkg_install_path, chksums)

    def _update_hook_permissions(self, pkg_name, pkg_install_path):
        '''
        Set permissions for folders controlled by vpm2
        Currently this applies only to the info/hooks folder
        @param pkg_name:
        @param pkg_install_path:
        '''
        hooks_r = os.path.join(pkg_install_path, META_DIR_NAME, HOOK_DIR_NAME)

        if os.path.exists(hooks_r):
            hooks = os.listdir(hooks_r)

            for h in hooks:
                #set mode for each hook script
                h_p = os.path.join(hooks_r, h)
                os.chmod(h_p, 00755)

    def _update_bundle_permissions(self, pkg_name, pkg_install_path):
        '''
        Set permissions for folders controlled by vpm2
        Currently this applies only to the info/hooks folder
        @param pkg_name:
        @param pkg_install_path:
        '''
        bundle_dir = os.path.join(pkg_install_path, BUNDLE_DIR_NAME)
        filemode_file = os.path.join(bundle_dir, FILEMODE_FILE_NAME)

        if os.path.exists(filemode_file):
            filemode_fc = read_file(filemode_file, False)

            #parse filemode file
            # <filemodes>
            #     <file path="/foo/bar" mode="755" owner="root" encoding="utf-8" />
            #     <directory path="/baz/bag" mode="755" owner="root" recursive="true" />
            # </filemodes>
            try:
                f = []
                filemodes = xml.dom.minidom.parse(filemode_fc)

                for entry in filemodes.firstChild.childNodes:
                    if entry.nodeName == 'file':
                        path = entry.getAttribute("path").strip()
                        mode = entry.getAttribute("mode").strip()
                        owner = entry.getAttribute("owner").strip()
                        #enc = entry.getAttribute("encoding").strip()

                        fe = {'path':path, 'mode':mode, 'owner':owner}
                    elif entry.nodeName == 'directory':
                        path = entry.getAttribute("path").strip()
                        mode = entry.getAttribute("mode").strip()
                        owner = entry.getAttribute("owner").strip()

                        if entry.getAttribute("recursive").strip().lower() == 'true':
                            rec = True

                        fe = {'path':path, 'mode':mode, 'owner':owner, 'recursive':rec}
                    else:
                        continue

                    f.append(fe)

                #
                owd = os.getcwd()

                os.chdir(bundle_dir)
                os.chroot(bundle_dir) # set root to bundle

                #apply file modes
                for fe in f:
                    #set mode for each hook script
                    path = fe.get('path')
                    mode = fe.get('mode').zfill(4)

                    owner_group = fe.get('owner').strip()

                    if fe.get('recursive'):
                        cmd = ['chmod', '-R', mode, path]
                        call(cmd)

                        cmd = ['chown', '-R', owner_group, path]
                        call(cmd)
                    else:
                        os.chmod(path, mode)

                        owner, group = -1
                        owner, group = owner_group.split(':')
                        os.chown(path, owner, group)

                os.chroot('/') #change root back
                os.chdir(owd)
            except:
                raise PackageError("Could not apply file modes")

    def _install_tree_files(self, pkg_name, src_root, dst_root):
        Package._tree_copy(pkg_name, src_root, dst_root, True)

        #set +x chmod on hook dir
        self._update_hook_permissions(pkg_name, dst_root)
        self._update_bundle_permissions(pkg_name, dst_root)

        # create data directories
        self._create_data_directories(dst_root)

        # TODO: is this still required?
        # tree files don't have a list of files or checksums, so we create
        # them on the fly here.  this calls tar again, but the operation
        # should be cheap since the layout is almost certainly still in the
        # fs cache
        # self._update_filelist_and_checksums(dst_root)    

    def _create_data_directories(self, dst_root):
        data_dir = os.path.join(dst_root, DATA_DIR_NAME)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        os.chmod(data_dir, 01777)

        for dir in DATA_DIRS:
            p = os.path.join(data_dir, dir)
            if not os.path.exists(p):
                os.mkdir(p)

            os.chmod(p, 01777)

    def _set_shared_locations(self, pkg_root):
        bundle_root = os.path.join(pkg_root, BUNDLE_DIR_NAME)

        dot_data = os.path.join(bundle_root, DOT_DATA_DIR_NAME)
        if not os.path.exists(dot_data):
            os.mkdir(dot_data)

        owd = os.getcwd()

        os.chdir(dot_data)
        for p in DATA_DIRS:
            src = os.path.join('..', '..', DATA_DIR_NAME, p)

            if os.path.exists(src):
                os.symlink(src, p)

        os.chdir(owd)

    def _del_shared_locations(self, pkg_root):
        dot_data = os.path.join(pkg_root, BUNDLE_DIR_NAME, DOT_DATA_DIR_NAME)

        if os.path.exists(dot_data):
            self._rm_rf(dot_data)

    def _remove(self, name, info, deploy_mode, mode = __ACTION_REMOVE):
        # files  = self.__pdb.read_package_file(name, FILELIST_FILE_NAME)
                
        prer_h = self.__pdb.find_package_file(name, PRE_REMOVE_NAME)
        pstr_h = self.__pdb.find_package_file(name, POST_REMOVE_NAME)
                
        root = info[KEY_INSR] or self.env.install_root
        if info[KEY_INSR] == '':
            root = self.env.install_root
        
        vs_root = os.path.join(root, info[KEY_INSN])

        hooks = None

        # Full chain is stopped before remove is called

        # 3. deconfigure dependees
        hooks = self._deconfigure_cartridges(info, vs_root)

        # 4. pre-remove hook
        rem_h_env = self._set_default_hook_env(vs_root)

        self._run_hook(prer_h, rem_h_env)

        # 5. remove/purge self
        # some apps create crud in their roots and _remove_files currently
        # is tripped up by at least directories created by apps, so until we
        # have a solution for how to deal with such files, we'll just rm -rf
        # everything.
        #
        # self._remove_files(root, files.splitlines())

        if mode == self.__ACTION_REMOVE:
            self._rm_rf(vs_root)
        elif mode == self.__ACTION_PURGE:
            # FIXME: perform actual purge, whatever that's going to be
            self._rm_rf(vs_root)

        # 6. run post-remove hook
        self._run_hook(pstr_h, rem_h_env)

        self._del_shared_locations(vs_root)

        return hooks

    def _purge_remove_aux(self, name, mode, deploy_mode = None):
        ''' Remove or purge a package. Remove deinstalls the package but
        leaves data and history around. Purge removes all traces of the
        package.
        
        @param name: Package name
        @param mode: purge or remove mode
        @param deploy_mode: deploy mode
        '''
        res = True
        err = None
        
        info = None

        try:
            self.db().lock('w')
            try:
                info = self.db().lookup(name)
                
                status = info.get(KEY_STAT, DB.UNKNOWN)
                virtual = info.get(KEY_DT_VIRT, False)
                
                if status in DB.REMOVABLE and not virtual:
                    try:
                        r, v, er = self.stop(name)
                    except Exception, e:
                        self.env.log.exception(e)
                        print ("Package '%s' can not be stopped, can't remove: %s" % (name, er))
                        if self.env.debug:
                            raise

                    # FIXME: package state should indicate if pkg is running   
                    #if er is not None:
                    #    raise PackageError(("Package '%s' can not be stopped, can't remove" % name))

                    ok, err = self.__pdb.check_remove(name)

                    if ok:
                    #try:
                        hooks = self._remove(name, info, deploy_mode, mode)

                        if hooks:
                            for h in hooks:
                                self._run_hook(h,
                                               {'VS_ACTION': VS_ACTION_REMOVE})
                    #finally:
                        self.db().commit_remove(info)

                else:
                    # check for prospective db and dt entries
                    if info is not None:
                        self.db()._db_entry(name, None)

                        #remove package from dependecy table        
                        # and remove package from any package depending on this package
                        self.db().remove_dependency_table_info(name)
                    
                    err = "Package '%s' is %s, can't remove" % (name, status)
            finally:
                self.db().unlock()
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug:
                raise

        return res, None, err

    # ------------------------------------------------------------------------
    #
    # API
    #
    # API functions return a tuple with three values, a boolean result code
    # indicating success ('True') or failure ('False'), the method's return
    # value or 'None' if the method is a procedure, and finally an error
    # value.  If this error value is not 'None' but the result code is
    # 'True', it indicates a warning.  If the result code is 'False', it
    # indicates an error.
    #
    # The error value is typically a string message.  However, 'install()',
    # 'remove()', as well as 'installable()' and 'removable()' may also
    # return a list of dictionaries if the operation failed (or would fail)
    # due to dependency errors.  Each of these dictionaries describes one
    # particular dependency error. The data structure is
    #
    #   {'Name'      : <package name>,
    #    'Version'   : <package version>,
    #    'Build'     : <vostok build number>,
    #    'Depends'   : <list of unsatisfied depends clauses> or 'None'
    #    'Conflicts' : <list of conflicting packages> or 'None'}
    #
    # If not 'None', the 'Depends' or 'Conflicts' lists, contain the same
    # string representations of clauses as 'control' files.  Example:
    #
    #   'Depends' : ['www-static.apache2 (>= 2.4)', ...]
    #
    # Note: 'install()' and 'remove()' are not idempotent.

    # FIXME: improve on transactionality of install/remove

    def pack(self, build_root, dest_dir):
        '''
        Pack up an already built or previously unpacked package located in
        'build_root' and place the resulting package
        in 'dest_dir'.  Returns the package basename or None in case of
        error.
        @param build_root: File location
        @param dest_dir: Where to store the vpm file
        '''
        res = True
        val = None
        err = None

        # place lock in application dir instead of self.env.lock_dir to
        # avoid having to deal with application paths
        # ('www-static/apache2-x.y.z' is different from
        # 'www-dynamic/apache2-x.y.z')

        # ensure paths are absolute
        build_root = os.path.abspath(build_root)
        dest_dir = os.path.abspath(dest_dir)

        try:
            self._lock(build_root, 'r')
            try:
                #val contains the package name
                res, val = self._pack(build_root, dest_dir)
            finally:
                self._unlock(build_root)
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug:
                raise

        return res, val, err


    def unpack(self, package, dest_dir):
        '''
        Unpack a VPM file
        @param package: Path to VPM package
        @param dest_dir: Path to extract to
        '''
        res = True
        val = None
        err = None

        dest_dir = os.path.abspath(dest_dir)

        try:
            rm_dest_dir = False
            dest_dir = os.path.abspath(dest_dir)

            if not os.path.exists(dest_dir):
                os.mkdir(dest_dir)
                rm_dest_dir = True

            try:
                info = None
                dst_rn = None

                if not os.path.isdir(dest_dir):
                    raise IOError("not a directory: '%s'" % dest_dir)

                pkg_temp_path = self._unpack(package)

                info = self._load_info_from_tree(pkg_temp_path)

                dst_rn = os.path.join(dest_dir, info[KEY_INSN])

                if not os.path.exists(dst_rn):
                    os.mkdir(dst_rn)
                elif os.path.exists(dst_rn):
                    self._rm_rf(dst_rn)

                Package._tree_copy(info[KEY_INSN], pkg_temp_path, dst_rn, True)

                self._rm_rf(pkg_temp_path)

                val = [dst_rn, info]
            finally:
                if rm_dest_dir and val is None:
                    self._rm_rf(dest_dir)
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug:
                raise

        return res, val, err

    # Added upon Lili's request so Flex has a package name before pack() is
    # called.
    def package_name(self, control_file, build_file = None):
        '''
        Load package name from control file
        @param control_file: path to control file
        @param build_file: path to build file
        '''

        res = True
        val = None
        err = None

        try:
            info = self._load_info_from_files(control_file, build_file)
            pkg__e = '.' + VPM_PKG_EXTENSION
            pkg__b = self._make_package_name(info)

            val = pkg__b + pkg__e
        except Exception, e:
            res = False
            self.env.log.exception(e)
            err = e
            if self.env.debug: raise

        return res, val, err

    def install(self, package, dest_root = None, deploy_mode = None):
        '''
        Install packages either in packed (.vpm) or unpacked form
        @param package: the package to install
        @param dest_root: Alternative install location
        @param deploy_mode: Deploy mode
        '''
        res = True
        val = None
        err = None

        if deploy_mode == None:
            deploy_mode = DEPLOY_MODE_MANUAL

        if not os.path.exists(package):
            val = False
            err = "'%s' not found." % package
            
            return res, val, err
        
        try:
            configure = True
            brk = False
            src_dir = None

            self.env.log.info("Installing '%s'" % package)
            self.db().lock('w')

            try:
                is_archive = not os.path.isdir(package)
                dst_root   = None
                in_tree    = False

                if package == dest_root and is_archive is False:
                    in_tree = True

                info = None
                ok = None

                #uploaded
                if dest_root is not None:
                    dest_root = os.path.abspath(dest_root)

                if is_archive:
                    self._validate_package(package)
                    info = self._load_info_from_archive(package)
                else:
                    info = self._load_info_from_tree(package)

                info[KEY_STAT] = DB.VERIFIED
                #verified

                ok, err = self.db().check_install(info)

                if ok is False:
                    #FIXME: find better condition
                    if info[KEY_TYPE] == VAL_TYPE_CRT:
                        raise PackageError("Cartridge dependencies are missing")
                    else:
                        for er in err:
                            if er[KEY_DEPS] is not None:
                                configure = False
    
                            if er[KEY_CONF] is not None:
                                configure = False
                                brk = True
    
                        err = None # Reset error state

                #query package status
                if not in_tree:
                    status = self.db().status(info[KEY_INSN])
                    
                    if status in DB.REMOVABLE:
                        #FIXME: begin transaction, save old package state

                        # set pkg set to committed for all packages depending 
                        # on this package. They get reconfigured upon start()
                        dep_pkg = self.db().find_depending_packages(
                                                                info[KEY_INSN])

                        for d_p in dep_pkg:
                            d_p_info = self.db().lookup(d_p)
                            self.db().set_package_state(d_p_info, DB.COMMITTED)

                        oinfo = self._load_info_from_db(info[KEY_INSN])
                        virtual = oinfo.get(KEY_DT_VIRT, False)
                        
                        hooks = None
                        if not virtual:
                            hooks = self._remove(oinfo[KEY_INSN], oinfo, deploy_mode)
                            
                        if hooks:
                            # FIXME right now we only return RESTART but
                            # once we actually return hooks, we may have
                            # to run them here--except if they are run
                            # after commit_install() as well, in which
                            # case we can skip them here
                            pass

                if is_archive:
                    src_dir = self._unpack(package)
                else:
                    src_dir = package
                #unpacked

                if dest_root is None:
                    if info[KEY_TYPE] == VAL_TYPE_CRT:
                        dest_root = self.env.cartridge_dir
                    elif info[KEY_TYPE] == VAL_TYPE_PKG:
                        dest_root = self.env.package_dir
                    elif info[KEY_TYPE] == VAL_TYPE_APP:
                        dest_root = self.env.application_dir

                info[KEY_INSR] = dest_root

                dst_root = os.path.join(dest_root, info[KEY_INSN])

                if not in_tree and not os.path.exists(dst_root):
                    os.mkdir(dst_root)

                # Run hook from tmp dir
                prei_h = os.path.join(src_dir, META_DIR_NAME, 
                                      HOOK_DIR_NAME, PRE_INSTALL_NAME)

                prei_h_env = self._set_default_hook_env(dst_root)

                # FIXME: preinstall hook
                self._run_hook(prei_h, prei_h_env)

                if not in_tree:
                    self._install_tree_files(info[KEY_INSN], src_dir, dst_root)

                self._set_shared_locations(dst_root)

                # Files in place, build hook root
                hook_root = os.path.join(dst_root, META_DIR_NAME, HOOK_DIR_NAME)
                psti_h = os.path.join(hook_root, POST_INSTALL_NAME)

                psti_h_env = self._set_default_hook_env(dst_root)

                self._run_hook([psti_h], psti_h_env)
                # file install complete   

                self.db().commit_install(info)

                if brk:
                    self.db().set_package_state(info, DB.BROKEN)

                #FIXME: end transaction, package install succeeded 
                #imported->committed
                
                #self.resolve_package_chain(info, info[KEY_NAME])                

                if configure:
                    try:
                        self._configure_cartridges(info, dst_root)

                        if deploy_mode != DEPLOY_MODE_MANUAL:
                            self.start(info[KEY_NAME])
                    except Exception, e:
                        self.env.log.exception(e)

                val = info[KEY_INSN]
            finally:
                if not in_tree and is_archive and src_dir:
                    self._rm_rf(src_dir)

                self.db().unlock()
        except Exception, e:
            #cleanup
            if dst_root is not None and os.path.exists(dst_root):
                self._rm_rf(dst_root)

            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug:
                raise

        return res, val, err


    def remove(self, name, deploy_mode = None):
        '''
        Remove package
        @param name: The package to be removed
        @param deploy_mode: Deploy mode
        '''

        self.env.log.info("Removing package: %s" % name)

        if deploy_mode == None:
            deploy_mode = DEPLOY_MODE_MANUAL

        return self._purge_remove_aux(name, self.__ACTION_REMOVE, deploy_mode)

    def purge(self, name, deploy_mode = None):
        '''
        Remove package
        @param name: The package to be removed
        @param deploy_mode: Deploy mode
        '''

        self.env.log.info("Purging package: %s" % name)

        if deploy_mode == None:
            deploy_mode = DEPLOY_MODE_MANUAL

        return self._purge_remove_aux(name, self.__ACTION_PURGE, deploy_mode)

    # Package is either in packed (.vpm) or unpacked form.
    def installable(self, package):
        '''
        Test wether a VPM or Unpacked Package is installable, i.e. if all
        dependencies are met etc...
        @param package: Path to VPM or Folder
        '''

        res = True
        val = None
        err = None

        try:
            self.db().lock('r')
            try:
                is_archive = not os.path.isdir(package)
                info = None

                if is_archive:
                    self._validate_package(package)
                    info = self._load_info_from_archive(package)
                else:
                    info = self._load_info_from_tree(package)

                val, err = self.__pdb.check_install(info)
# FIXME: fix this: return correct package state BUGZID: 2466                
#                configure = True
#                brk = False
#                if val is False:
#                    for er in err:
#                        if er[KEY_DEPS] is not None:
#                            configure = False
#
#                        if er[KEY_CONF] is not None:
#                            configure = False
#                            brk = True
#
#                    err = None # Reset error state
#                
#                if brk:
#                    res = False
#                    val = DB.BROKEN
#                else:
#                    if not configure:
#                        res = True
#                        val = DB.CO
            finally:
                self.__pdb.unlock()
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug: raise

        return res, val, err


    def removable(self, name):
        '''
        Remove an installed package.

        @param name: package name
        '''
        res = True
        val = None
        err = None

        try:
            self.db().lock('r')
            try:
                val, err = self.__pdb.check_remove(name)
            finally:
                self.__pdb.unlock()
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug: raise

        return res, val, err

    def info(self, name):
        '''
        Get package information.

        @param name: package name
        '''
        res = True
        val = None
        err = None

        try:
            #FIXME: Discuss
            # disable locking for demo. issue is that during app
            # install, the db is write locked, but then the app start hook
            # is run and calls "cartrigde" command which call us (info) here
            # so we can't acquire the lock
            # self.db().lock('r')
            #try:
                status = self.db().status(name)

                if status in DB.KNOWN:
                    val = self._load_info_from_db(name)
#            finally:
#                pass
#                #self.__pdb.unlock()
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug: raise

        return res, val, err

    def list_available(self, roles = [], repositories = []):
        available = {'local':[]}

        if len(roles) == 0:
            available['local'] = self.db().filter_packages(KEY_ROLE)
        else:
            available['local'] = self.db().filter_packages(KEY_ROLE, roles)

        # TODO: repository feature
        #if len(repositories) != 0:
        #    for repo in repositories:

        return available

    def start(self, package, app_env=None):
        '''
        Start the package named <package>.

        @param package: package name
        @param app_env: application environment
        '''
        res = True
        val = None
        err = None

        try:
            self.db().lock('w')
            try:
                info = self.db().lookup(package)

                if info is None or not info[KEY_TYPE] is VAL_TYPE_APP:
                    raise PackageError("Cartridges can not be started directly")

                #if info[KEY_STAT] is DB.COMMITTED:
                self.resolve_package_chain(info, package)
                    
                # package state is now resolved. Both calls would first look
                # whether the package has a start or stop hook.
                pkg_root = os.path.join(info[KEY_INSR], info[KEY_INSN])

                start_hook = os.path.join(pkg_root,
                                          META_DIR_NAME,
                                          HOOK_DIR_NAME,
                                          START_NAME)

                start_h_args = [package]

                # TODO: Replace this with proper handling of supplying
                # the runtime, www-dynamic and www-static as arguments
                # to app or delegated start hooks.
                if info[KEY_DEPS] is not None:
                    for dep in info[KEY_DEPS]:
                        # FIXME: THIS WON'T WORK FOR OR'ED DEPENDENCIES
                        dep_name=dep[0]['Name']
                        dep_info=self.db().lookup(dep_name)
                        if dep_info[KEY_ROLE] == VAL_ROLE_DYN:
                            start_h_args.append(dep_name)
                            break

                if not os.path.isfile(start_hook):
                    delegate = info.get(KEY_DLGT, None) #info[KEY_DLGT] or None

                    if delegate is not None:
                        # Lookup delegate and check for start hook
                        delegate_pkg = self.db().lookup(delegate)

                        if not delegate_pkg is None:
                            delegate_start_hook = \
                                os.path.join(delegate_pkg[KEY_INSR],
                                             delegate_pkg[KEY_INSN],
                                             META_DIR_NAME,
                                             HOOK_DIR_NAME,
                                             START_NAME)

                            if os.path.isfile(delegate_start_hook):
                                start_hook = delegate_start_hook

                                start_h_env = \
                                    self._set_default_hook_env(\
                                    os.path.join(delegate_pkg[KEY_INSR],
                                                 delegate_pkg[KEY_INSN]))

                                delegate = None
                            else:
                                raise PackageError(("Package %s can not "
                                                    "start. Delegate %s is "
                                                    "not startable"
                                                    % (info[KEY_NAME],
                                                       delegate_pkg[KEY_NAME])))
                    else:
                        raise PackageError(
                                ("Package %s can not start. "
                                 "Startable delegate is missing"
                                 % info[KEY_NAME]))
                else:
                    #call start hook
                    start_h_env = self._set_default_hook_env(pkg_root)

                # FIXME: hardcoded start hook parameters
                start_h_args.insert(0, start_hook)
                
                if app_env is not None:
                    start_h_env.update(app_env)

                # capture stdout and stderr, return in err
                o, e, val = self._run_hook(start_h_args, start_h_env)
                err = [o, e]
            finally:
                self.db().unlock()
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug:
                raise

        return res, val, err

    def stop(self, package, app_env=None):
        '''
        Stop package <package>.

        @param package: package name
        @param app_env: application environment
        '''
        res = True
        val = None
        err = None

        try:
            info = None

            # Load package data from db
            o_info = self.db().lookup(package)
            
            if o_info is None:
                raise PackageError("Cartridges can not be stopped directly")

            list = []

            if o_info[KEY_TYPE] is not VAL_TYPE_APP:
                # find anything that depends on this
                dt = self.db().get_dependency_table_info(o_info[KEY_NAME])                

                if dt is not None:
                    for l in dt:
                        prov = l[KEY_DT_PROV]

                        prov_info = self.db().lookup(prov[KEY_NAME])

                        if prov_info[KEY_TYPE] is VAL_TYPE_APP:
                            #add app to list
                            list.append(prov_info)
                
                list.append(o_info) #append app
            else:
                list.append(o_info)

            # iterate over list of apps
            for info in list:
                pkg_root = os.path.join(info[KEY_INSR], info[KEY_INSN])

                stop_hook = os.path.join(pkg_root,
                                         META_DIR_NAME,
                                         HOOK_DIR_NAME,
                                         STOP_NAME)
                
                stop_h_args=[ info[KEY_NAME] ]

                # TODO: Replace this with proper handling of supplying
                # the runtime, www-dynamic and www-static as arguments
                # to app or delegated start hooks.
                if not info[KEY_DEPS] is None:
                    for dep in info[KEY_DEPS]:
                        # FIXME: THIS WON'T WORK FOR OR'ED DEPENDENCIES
                        dep_name=dep[0][KEY_NAME]
                        dep_info=self.db().lookup(dep_name)
                        if dep_info[KEY_ROLE] == VAL_ROLE_DYN:
                            stop_h_args.append(dep_name)
                            break

                if not os.path.isfile(stop_hook):
                    delegate = info.get(KEY_DLGT, None)

                    if delegate is not None:
                        # Lookup delegate and check for stop hook
                        delegate_pkg = self.db().lookup(delegate)

                        delegate_stop_hook = \
                            os.path.join(delegate_pkg[KEY_INSR],
                                         delegate_pkg[KEY_INSN],
                                         META_DIR_NAME,
                                         HOOK_DIR_NAME,
                                         STOP_NAME)

                        if os.path.isfile(delegate_stop_hook):
                            stop_hook = delegate_stop_hook

                            stop_h_env = \
                                self._set_default_hook_env(\
                                os.path.join(delegate_pkg[KEY_INSR],
                                             delegate_pkg[KEY_INSN]))
                        else:
                            raise PackageError("Package %s can not stop. "
                                               "Delegate %s is not stopable"
                                               % (info[KEY_NAME],
                                                  delegate_pkg[KEY_NAME]))
                    else:
                        raise PackageError(
                                ("Can not stop Package %s. "
                                 "Stoppable delegate is missing"
                                 % info[KEY_NAME]))

                else:
                    #call stop hook
                    stop_h_env = self._set_default_hook_env(pkg_root)

                # FIXME: hardcoded start hook parameters
                stop_h_args.insert(0, stop_hook)

                if app_env is not None:
                    stop_h_env.update(app_env)

                # capture stdout and stderr, return in err
                o, e, val = self._run_hook(stop_h_args, stop_h_env)
                err = [o, e]
        except Exception, e:
            res = False
            err = e
            self.env.log.exception(e)
            if self.env.debug:
                raise

        return res, val, err

    def restart(self, package):
        res, val, err = self.stop(package)

        if res:
            res, val, err = self.start(package)

        return res, val, err

    def get_control_info(self, path):
        '''
        Return the parsed information stored in control file <path>.

        @param path: control file pathname
        '''
        res = True
        val = None
        err = None

        if isinstance(path, basestring):
            try:
                cinfo = self._load_control_info_from_tree(path)

                self._process_control_info(cinfo, path)
                val = cinfo
            except Exception, e:
                res = False
                err = e
                self.env.log.exception(e)
                if self.env.debug:
                    raise
        else:
            res = False
            err = "invalid argument"

        return res, val, err

    def get_build_info(self, path):
        '''
        Return the parsed information stored in build file <path>.

        @param path: build file pathname
        '''
        res = True
        val = None
        err = None

        if isinstance(path, basestring):
            try:
                binfo = self._load_build_info_from_tree(path)

                self._process_build_info(binfo, path)
                val = binfo
            except Exception, e:
                res = False
                err = e
                self.env.log.exception(e)
                if self.env.debug:
                    raise
        else:
            res = False
            err = "invalid argument"

        return res, val, err

    def set_control_info(self, cinfo, path):
        '''
        Set the control file <path> to the information stored in <cinfo>.

        @param cinfo: control file information
        @param path: control file pathname
        '''
        res = True
        val = None
        err = None

        if isinstance(cinfo, dict) and isinstance(path, basestring):
            try:
                # '<none>' (for lack of a better name) means "in memory"
                self._validate_fields(cinfo,
                                      CKEYS_REQ + BKEYS_REQ,
                                      CKEYS_OPT + CKEYS_QUO,
                                      '<none>')
                data = ""
                format = "%s: %s\n"

                # Keys in CKEYS_REQ and CKEYS_OPT are already in canonical order
                for k in CKEYS_REQ:
                    data += format % (k, cinfo[k])

                for k in CKEYS_OPT:
                    if k in cinfo:
                        if k is KEY_PROV:
                            s = self._provides2str(cinfo[k], cinfo[KEY_NQUO])
                        elif k is KEY_DEPS or k is KEY_CONF:
                            if cinfo[k] is None:
                                s = ''
                            else:
                                s = self._relation2str(cinfo[k])
                        else:
                            s = cinfo[k]

                        data += format % (k, s)

                write_file(path, data)
                
                #add inactive entry to dependency table
                if cinfo[KEY_DEPS]:                    
                    # enable virtual mode
                    self.db()._dt_register_deps(cinfo, True)
                    
                self.db()._db_entry(cinfo[KEY_NAME], cinfo, True)                    
                    
            except Exception, e:
                res = False
                err = e
                self.env.log.exception(e)
                if self.env.debug:
                    raise
        else:
            res = False
            err = "invalid arguments"

        return res, val, err

    def set_build_info(self, binfo, path):
        '''
        Set the build file <path> to the information stored in <binfo>.

        @param binfo: build file information
        @param path: build file pathname
        '''
        res = True
        val = None
        err = None

        if isinstance(binfo, dict) and isinstance(path, basestring):
            try:
                # '<none>' (for lack of a better name) means "in memory"
                self._validate_fields(binfo, BKEYS_REQ, BKEYS_OPT, '<none>')
                data = ""
                format = "%s: %s\n"

                # Keys in BKEYS_REQ and BKEYS_OPT are already in canonical order
                for k in BKEYS_REQ:
                    data += format % (k, binfo[k])

                for k in BKEYS_OPT:
                    if k in binfo:
                        data += format % (k, binfo[k])

                write_file(path, data)
            except Exception, e:
                res = False
                err = e
                self.env.log.exception(e)
                if self.env.debug:
                    raise
        else:
            res = False
            err = "invalid arguments"

        return res, val, err

    # scaffolding directory is
    # <package>/info/defaults/<quoted-package-name>. The IDL path is
    # <package>info/defaults/idl.py.
    def get_scaffolding(self, provider = None, dependency = None, dependant = None):
        res = True
        val = None
        err = None
        
        try:
            if provider is None:
                # get provider for dependency
                if not dependency is None and not dependant is None:

                    prov = None
                    
                    for dep in dependency:
                        # search provider for p
                        tmp = self.db().find_feature_packages(dep[KEY_NAME], dependant)
                        
                        if prov is None:
                            prov = tmp[KEY_NAME]
                        else:
                            if tmp[KEY_NAME] == prov:
                                # Or relation found
                                break
                            else:
                                raise PackageError("Invalid dependency structure input")
                    
                    if not prov is None:
                        provider = prov
                else:
                    raise PackageError("Dependency and dependant must be set")
                                   
            ###known                                      
            provider_info = self.db().lookup(provider)                    
            
            if provider_info is not None:                                    
                defaults_dir = os.path.join(provider_info[KEY_INSR],
                                            provider_info[KEY_NQUO],
                                            META_DIR_NAME,
                                            DEFAULTS_DIR_NAME)
                
                scaffolding_dir = os.path.join(defaults_dir,
                                               provider_info[KEY_NQUO])
                
                scaffolding_path = None
                if os.path.exists(scaffolding_dir):
                    scaffolding_path = scaffolding_dir
                
                idl_file = os.path.join(defaults_dir, IDL_FILE_NAME)
                
                idl_path = None                
                if os.path.exists(idl_file):
                    idl_path = idl_file
                
                val = [provider_info, idl_path, scaffolding_path]
            else:
                raise PackageError("Provider not found")
                                
        except Exception, e:
            res = False
            val = None
            err = e        
        
        return res, val, err
    
    # setup directory is <package>/info/setup/<name> where <name> is either
    # a literal dependency or a name associated with a dependency based on
    # the mapping file
    def get_setup_directory(self, package_name, dependency, shared):
        res = True
        val = []
        err = None
        
        try:
            if dependency is None:
                raise PackageError("Invalid dependency")
  
            pkg = self.db().lookup(package_name)
            
            dep_info = self.db().lookup(dependency)
            
            if pkg is None and dep_info is None:
                raise PackageError("Package or dependency not found")
            
            setup_path = None
            
            if shared is True:
                if pkg[KEY_TYPE] == VAL_TYPE_APP:
                    insr = pkg.get(KEY_INSR, None)
                    if insr is None:                    
                        insr = self.env.application_dir
                        
                    setup_path = os.path.join(insr,
                                              pkg[KEY_NQUO],
                                              SHARED_COPY_LINK_NAME,
                                              META_DIR_NAME,
                                              SETTINGS_DIR_NAME)
                else:
                    raise PackageError("'shared' only applies to applications")
            else:
                insr = pkg.get(KEY_INSR, None)
                if insr is None:                    
                    if pkg[KEY_TYPE] == VAL_TYPE_CRT:
                        insr = self.env.cartridge_dir
                    elif pkg[KEY_TYPE] == VAL_TYPE_PKG:
                        insr = self.env.package_dir
                    elif pkg[KEY_TYPE] == VAL_TYPE_APP:
                        insr = self.env.application_dir
                        
                setup_path = os.path.join(insr,
                                          pkg[KEY_NQUO],
                                          META_DIR_NAME,
                                          SETTINGS_DIR_NAME)
                
            if setup_path is not None:
                # parse mapping
                dep_path = self._settings_resolve_mapping(setup_path,
                                                          None,
                                                          dep_info[KEY_INSN])
                
                path = os.path.join(setup_path, dep_path)
                if os.path.exists(path):
                    val = [path, True]
                else:
                    val = [path, False]
            else:
                raise PackageError("Setup path not found")
                 
        except Exception, e:
            res = False
            val = [None, False]
            err = e
            
        return res, val, err

    # Trivial wrappers around _safe_quote and _safe_unquote above.
    def quote_string(self, string):
        return self._safe_quote(string)

    def unquote_string(self, string):
        return self._safe_unquote(string)


#    def get_file_list(self, name):
#        '''
#        This method gets the file list installed for a package
#        @param name: package name
#        '''
#
#        self.env.log.info("Getting installed file list for package: %s" % name)
#
#        res = True
#        err = None
#        value = None
#        try:
#            self.db().lock('r')
#            try:
#                value  = self.__pdb.read_package_file(name, FILELIST_FILE_NAME)
#            finally:
#                self.__pdb.unlock()
#        except Exception, e:
#            res = False
#            err = e
#            if self.env.debug: raise
#
#        return res, value, err


    # *****************************************************************
    # FIXME these will be accessible through a "vostok" command
    # *****************************************************************

    # FIXME: are these still called?
    def get_cartridge_install_dir(self, cartridge_name):
        res, info, err = self.info(cartridge_name)

        if res:
            cartridge_install_dir = os.path.join(info[KEY_INSR],
                                                 info[KEY_INSN])
            return cartridge_install_dir
        else:
            raise Exception, err


    def get_cartridge_configuration_module(self, cartridge_name):

        cartridge_install_dir = self.get_cartridge_install_dir(cartridge_name)
        configure_module_dir = os.path.join(cartridge_install_dir,
                                        META_DIR_NAME, CFG_DIR_NAME)

        f, p, d = imp.find_module(CFG_BASENAME, [configure_module_dir])

        try:
            module = imp.load_module(CFG_BASENAME, f, p, d)
            configure_module = module.Configuration(cartridge_install_dir)
            return configure_module
        finally:
            if f:
                f.close()

    def add_module(self, cartridge_name):
        pass

    # Used by the 'vostok' command
    def get_hook(self, package, hook):
        '''
        Return the path of hook <hook> in package <package>.

        @param package: package name
        @param hook: hook name
        '''
        res = True
        val = None
        err = None

        if isinstance(package, basestring) and isinstance(hook, basestring):
            try:
                pkg = self.db().lookup(package)

                if pkg is not None:
                    h = os.path.join(pkg[KEY_INSR],
                                     pkg[KEY_INSN],
                                     META_DIR_NAME,
                                     HOOK_DIR_NAME,
                                     hook)                    

                    if os.path.exists(h):
                        val = h
                    else:
                        err = "'%s': unknown hook '%s'\n" % (package, h)
                else:
                    err = "unknown package '%s'\n" % package
            except Exception, e:
                res = False
                err = e
                self.env.log.exception(e)
                if self.env.debug:
                    raise
        else:
            res = False
            err = "invalid arguments"

        return res, val, err


    def get_bundle_dir(self, package):
        '''
        Return the bundle directory of package <package>.

        @param package: package name
        '''
        res = True
        val = None
        err = None

        if isinstance(package, basestring):
            try:
                pkg = self.db().lookup(package)

                if pkg is not None:
                    h = os.path.join(pkg[KEY_INSR],
                                     pkg[KEY_INSN],
                                     BUNDLE_DIR_NAME)

                    if os.path.exists(h):
                        val = h
                    else:
                        err = "'%s': bundle directory not found!\n" % package
                else:
                    err = "unknown package '%s'\n" % package
            except Exception, e:
                res = False
                err = e
                self.env.log.exception(e)
                if self.env.debug:
                    raise
        else:
            res = False
            err = "invalid arguments"

        return res, val, err



#
# EOF
