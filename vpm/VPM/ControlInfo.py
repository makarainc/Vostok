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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/VPM/ControlInfo.py $
# $Date: 2010-04-23 13:14:46 +0200 (Fr, 23 Apr 2010) $
# $Revision: 6959 $

import re
import urllib

from VPM.Exceptions import ControlFileError
from VPM.Constants import *
from VPM.Structures import *

class ControlInfo(object):
    '''
    classdocs
    '''
    
    # Internal data
    Virtual = False
    
    Running = False
    
    #
    # Control & Build File Fields
    # ---------------------------
    
    # Core information
    Name                = ''                 # this is the only required field
    
    Version             = '0.0.0'
    
    Build               = '1'                # start build numbers at '1'
    
    Architecture        = 'all'              # assume non-binary format
    ArchitectureValues  = frozenset(['i686', 'amd64', 'all'])
    
    # Provides, Depends, Conflicts are used for dependency declarations
    Provides            = ''                       
    Depends             = ''                       
    Conflicts           = ''
    
    # Additional informational fields
    Description         = ''                # text    
    Vendor              = ''                # e.g. IBM vs Sun JRE    
    DisplayName         = ''                # if that needs to be different  
      
    Delegate            = ''                # Empty by default 
                                            # Must be set explicitly    
                                            
    Bundles             = ''                # List of bundles, used at build time.    
    
    # Type is used internally (vpm's are treated differently based on type)
    Type                = VAL_TYPE_APP
    TypeValues          = frozenset([VAL_TYPE_CRT, VAL_TYPE_PKG, VAL_TYPE_APP])                    
    
    Role                = VAL_ROLE_APP
    RoleValues          = frozenset([VAL_ROLE_STA, VAL_ROLE_STA_E, VAL_ROLE_DYN, 
                                    VAL_ROLE_DYN_E, VAL_ROLE_RTM, VAL_ROLE_RTM_E, 
                                    VAL_ROLE_APP, VAL_ROLE_DBM, VAL_ROLE_DBM_E])
    
    ApplicationType     = '' # TODO: document
    
    #Tags = ''
    #VAL_TAG_RUN = 'runnable'
    #VAL_TAG_END = 'endpoint'
    #VAL_TAG_DEFAULT = frozenset([])
      
    # Parsed Control File Keys
    QuotedName          = ''
    QuotedVersion       = ''     
    
    # Install time settings
    InstallRoot         = ''    
    InstallName         = ''

    Status              = 'imported' # hack    
    PackageState        = PSTATE_VIRGIN
    
    # We keep these as ordered lists representing canonical ordering on write-out
    CKEYS_REQ = ['Name']
    CKEYS_OPT = ['Version', 'Architecture',              # core information
                 'Provides', 'Depends', 'Conflicts',    # dependencies
                 'Description', 'Vendor', 'DisplayName',    # addt'l information
                 'Delegate',                        # delgate pkg control
                 'Type', 'Role', 'ApplicationType',            # classification
                 'Bundles']
    
    BKEYS_REQ = ['Build']
    BKEYS_OPT = []
    
    __KEYS = ['Name', 'Version', 'Architecture', 'Provides', 'Depends', 
              'Conflicts', 'Description', 'Vendor', 'DisplayName', 'Delegate', 
              'Type', 'Role', 'ApplicationType', 'Bundles',
              'QuotedName', 'QuotedVersion', 'InstallRoot', 'InstallName',
              'Status', 'PackageState']

    __KEY_MAPPING = {'QuotedName'       : 'Quoted-Name',
                     'QuotedVersion'    : 'Quoted-Version',
                     'ApplicationType'  : 'Application-Type',
                     'PackageState'     : 'Package-State',
                     'InstallRoot'      : 'Install-Root',
                     'InstallName'      : 'Install-Name'
                     }
    
    def __init__(self, controlFileData, controlFileName):
        '''
        Constructor
        '''
        if controlFileData is not None:            
            if not isinstance(controlFileData, dict):
                controlFileData = self.__parse_control_file(controlFileData, controlFileName)
                
            self.__processControlInfo(controlFileData, controlFileName)
        
    def __str__(self):
        return self.toString()
    
    def toString(self):
        string = ''
        
        valid_keys = self.CKEYS_REQ + self.CKEYS_OPT
        for key in valid_keys:
            if key in self.__dict__:
                v = self.__dict__[key]
                if v is not None and v != '':
                    if key == 'Provides':
                        val = self._provides2str(v, self.Name)
                    elif key == 'Depends' or key == 'Conflicts':
                        val = self._relation2str(v)
                    else:
                        val = v
                    
                    if key in self.__KEY_MAPPING:
                        key = self.__KEY_MAPPING[key]
                            
                    string += '%s: %s\n' % (key,val)
        
        return string
    
    def toDict(self):
        res = {}
        
        for key in self.__KEYS:
            if key in self.__dict__:
                v = self.__dict__[key]
                if v is not None and v != '':
                    if key == 'Provides':
                        val = self._provides2str(v, self.Name)
                    elif key == 'Depends' or key == 'Conflicts':
                        val = self._relation2str(v)
                    else:
                        val = v
                    
                    if key in self.__KEY_MAPPING:
                        key = self.__KEY_MAPPING[key]
                            
                    res[key] = val
        
        return res
    
    def toStringBuild(self):
        string = 'Build: %s' % self.Build
        
        return string 
    
    def fromString(self, string):
        self.__processControlInfo(string, '<none>')
    
    def __processControlInfo(self, cinfo, cfile):
        self.__validateFields(cinfo, self.CKEYS_REQ, self.CKEYS_OPT, cfile)

        # Set attributes
        valid_keys = self.CKEYS_REQ + self.CKEYS_OPT
        for k, v in cinfo.iteritems():
            if k in valid_keys:
                self.__dict__[k] = v.strip()
            else:
                raise ControlFileError("ControlInfo: unknown key '%s' => '%s'" % (k,v))
        
        # Add quoted versions of the user-controlled name and version keys
        self.QuotedName = self._safe_quote(self.Name)
        self.QuotedVersion = self._safe_quote(self.Version)
        
        self.InstallName = self.Name

        # ensure Arch has a known value
        if self.Architecture.lower() not in self.ArchitectureValues:
            raise ControlFileError("%s: unknown architecture '%s'" %
                                   (cfile, self.Architecture))

        # ensure Type has a known value
        self.Type = self.Type.lower().capitalize()
        if self.Type not in self.TypeValues:
            raise ControlFileError("%s: unkonw package type '%s'" %
                                   (cfile, self.Type))

        # canonicalize optional values
        self.Provides = self.__canonicalizeProvides(self.QuotedName, self.QuotedVersion, self.Provides, cfile)
        
        # FIXME: maybe ensure package doesn't depend on or conflict with itself
        self.Depends = self.__canonicalizeRelation(self.Depends, cfile)
        
        self.Conflicts = self.__canonicalizeRelation(self.Conflicts, cfile)

    def _process_build_info(self, binfo, bfile):
        self.__validateFields(binfo, self.BKEYS_REQ, self.BKEYS_OPT, bfile)

        return binfo
    
    def __parse_control_file(self, cdata, cfile):
        return self._parse_declarations(cdata.splitlines(), cfile)
    
    def __validateFields(self, hash, required, optional, pathname):
        for k in required:
            #print k
            if k not in hash:
                raise ControlFileError("%s: missing required field '%s'" %
                                       (pathname, k))
            if not hash[k]:
                if k not in frozenset(['Install-Name']): # may be empty
                    raise ControlFileError("%s: missing value for required "
                                           "field '%s'" % (pathname, k))

        for k in hash.keys():
            if k not in required and k not in optional:
                raise ControlFileError("%s: unknown field '%s'" %
                                       (pathname, k))        
    
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
    def __canonicalizeProvides(self, name, version, string, file):
        res = []
        
        pi = ProvidesInfo(name, version, name + ' (' + version + ')')
        res.append(pi)        

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

                    val = ProvidesInfo(n, v, n + (v and ' (' + v + ')' or ''))
                    
                    if val not in res:
                        res.append(val)

        return res        
    
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
    def __canonicalizeRelation(self, string, file):
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

                        di = DependsInfo(n, p, n + t)
                        exp[j] = di

            res = seq

        return res
    
    def _safe_quote(self, string):
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
    
    @staticmethod
    def _provides2str(exprs, name):
        conj = []

        for e in exprs:
            # FIXME the 'Name' and 'Version' dictionary keys should be
            # really KEY_NQUO and KEY_VQUO since their respective values
            # must be quoted.
            if e.Name is not name: # omit name (provided automatically)
                conj.append(e.String)

        return ', '.join(conj)

    @staticmethod
    def _relation2str(exprs):
        conj = []

        for cj in exprs:
            disj = []

            for dj in cj:
                disj.append(dj.String)

            conj.append(' | '.join(disj))

        return ', '.join(conj)
    
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

    ## Getter/Setter methods
    ##
    def getAttrib(self, attribute):
        if attribute in self.__dict__:
            return self.__dict__[attribute]
        else:
            return None

    def setAttrib(self, attribute, value):
        if attribute in self.__dict__:
            self.__dict__[attribute] = value
            
    ## API Methods
    def setBuildInfo(self, buildinfo):
        self.Build = buildinfo['Build']
        
    def setStatus(self, status):
        self.Status = status
        
    def setRunning(self):
        self.Running = True
    
    def setStopped(self):
        self.Running = False
#EOF
