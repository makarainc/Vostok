#!/usr/bin/env python
# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/cartridge-support/Cartridge/Config.py $
# $Date: 2010-04-15 01:53:18 +0200 (Do, 15 Apr 2010) $
# $Revision: 6674 $

# 2.5 and higher only
#from __future__ import with_statement

import cPickle
import os
import sys
import shutil
import logging

log = logging.getLogger(__name__)

import Cartridge.Registry as Registry

VPM_TRACE=os.getenv('VPM_TRACE', None)

class VersionError (ValueError):
    pass

class Config (object):
    __API_VERSION = 1.0
    __REGISTRY_VERSIONS = ('1.0')

    # FIXME import from PackageManager
    BUNDLE_DIR_NAME    = 'bundle'
    META_DIR_NAME      = 'info'
    CFG_DIR_NAME       = 'configuration'
    REGISTRY_DB_NAME   = 'registry.db'
                      
    BUNDLE_DIR         = None
    CFG_DIR_PATH       = None
    __REGISTRY_DB_PATH = None


    # Option Levels
    NORMAL   = Registry.NORMAL
    ADVANCED = Registry.ADVANCED
    EXPERT   = Registry.EXPERT

    root           = None
    default_locale = None

    # cartridges with monolithic configuration may set _config_file
    # directly.  cartridges with per-owner config files must override
    # config_file().
    # FIXME remove -- every cartridge should just set this
    # explicitly when calling update(). Reason is that some files may be
    # private, other not, so having one global is stupid.  We use this as a
    # fallback for now.
    _config_file    = None
    private_config  = False
    complete_config = True

    def config_file(self, dummy = None):
        return self._config_file
    
    def __init__(self, root):
        self.root = root
        self.BUNDLE_DIR         = os.path.join(self.root,
                                               self.BUNDLE_DIR_NAME)
        self.CFG_DIR_PATH       = os.path.join(self.root,
                                               self.META_DIR_NAME,
                                               self.CFG_DIR_NAME)
        self.__REGISTRY_DB_PATH = os.path.join(self.CFG_DIR_PATH,
                                               self.REGISTRY_DB_NAME)
    
    @staticmethod
    def _marshal(data):
        return cPickle.dumps(data)

    @staticmethod
    def _unmarshal(data):
        return cPickle.loads(data)

    @staticmethod
    def _load_file(pathname, registry):
        p, f = os.path.split(pathname)
        n, _ = os.path.splitext(f)

        return registry.load_module(n, p)

    @staticmethod
    def _load_data(path):
        # 2.5 only
        # with open(path, 'rb') as f:
        #     return cPickle.load(f)
        f = open(path, 'rb')
        r = ''

        try:
            r = cPickle.load(f)
        finally:
            f.close()

        return r

    @staticmethod
    def _dump_data(data, path):
        # 2.5 only
        # with open(path, 'wb') as f:
        #     cPickle.dump(data, f)
        f = open(path, 'wb')

        try:
            cPickle.dump(data, f)
        finally:
            f.close()

    def _check_registry(self, registry):
        if not registry.version() in self.__REGISTRY_VERSIONS:
            raise VersionError \
                  ("Registry version '%s' not one of (%s)" % \
                   (registry.version(), ', '.join(self.__REGISTRY_VERSIONS)))
        
    def _new_registry(self):
        r = Registry.Registry(self.default_locale)
        
        self._check_registry(r)
        
        return r

    # Built-in Default Formatters
    @staticmethod
    def format_item(level, name, params):
        return '  ' * level + name + ': ' + str(params) + "\n"

    @staticmethod
    def format_group(level, name, params, format_content):
        return "\n" + \
               '  ' * level + '[' + name + ': ' + str(params) + "]\n" + \
               format_content(level + 1) + \
               "\n"

    @staticmethod
    def format_scope(level, name, params, format_content):
        return "\n" + \
               '  ' * level + name + ': ' + str(params) + " {\n" + \
               format_content(level + 1) + \
               '  ' * level + "}\n" + \
               "\n"
    
    def _set_formatters(self):
        Registry._item_formatter  = self.format_item
        Registry._group_formatter = self.format_group
        Registry._scope_formatter = self.format_scope

    def _write_config(self, registry,
                      owner = None, private = False, file = None):
        s = ''
        r = None
        
        self._set_formatters()
        s = registry.write_configuration(owner, private)

        if file:
            f = open(file, 'w')
            r = False

            try:
                f.write(s)
                r = True
            finally:
                f.close()
        else:
            r = s

        if VPM_TRACE:
            sys.stderr.write(("[Cartridge.Config.write_config]\n" +
                              "  owner   : %s\n" +
                              "  private : %s\n" +
                              "  file    : %s\n") % \
                             (str(owner), str(private), str(file)))
        
        return r

    # Default handler
    @staticmethod
    def install_files(owner, files = None, locale = None):
        pass

    @staticmethod
    def remove_files(owner, locale = None):
        pass
        

    #
    # API

    def version(self):
        return self.__API_VERSION

    # FIXME naming get/show
    def get(self, locale = None, level = None):
        r = self._load_data(self.__REGISTRY_DB_PATH)
        
        if locale == None:
            locale = self.default_locale
        if level == None:
            level = Config.NORMAL

        r.select_locale(locale)
        r.select_level(level)

        return self._marshal(r)

    def show(self, data):
        r = self._unmarshal(data)

        self._check_registry(r)

        return r

    # settings is a string containing already loaded settings data
    #
    # FIXME: don't update or dump in case of error
    def update(self, owner, settings_data,
               locale = None, config_file = None, private = None):
        res = ''
        cfg = config_file or self.config_file(owner)
        reg = self._load_data(self.__REGISTRY_DB_PATH)
        prv = private or self.private_config

        if settings_data:                    # install/update
            # s = self._load_file(settings_data, reg)
            exec settings_data               # this defines 'settings'

            # limit updates to EXPERT (i.e. prohibit LOCKED item updates)
            reg.select_level(Config.EXPERT)

            # if 'settings' in dir(s):
            reg.update_settings(owner, settings)
            self._dump_data(reg, self.__REGISTRY_DB_PATH)
            if prv:
                # Some cartridges (e.g. PHP) require private dependent
                # configuration but can't chain-load files. As a result,
                # dependent configuration needs to be merged with the
                # maintainer config. This can be achieved by setting
                # "private_config" to "True" but "complete_config" to "False".
                # We then pass 'private = False' to Configuration.write().
                #
                # This works because Registry.Configuration.write()
                # will select both the maintainer config and an additional
                # owner IFF we pass an owner but set 'private' to "False".
                #
                # WARNING: due to the way this is implemented, the
                # maintainer configuration is written first, and then the
                # owner configuration. This happens to work out great for
                # PHP, but there is no way currently to specify the
                # behavior. FIXME: this needs to be fixed.
                if self.complete_config:
                    p = True
                else:
                    p = False
                self._write_config(reg,
                                   owner = owner, private = p, file = cfg)
            else:
                self._write_config(reg,
                                   owner = None, private = False, file = cfg)
        else:                           # remove
            reg.update_settings(owner, None)
            self._dump_data(reg, self.__REGISTRY_DB_PATH)

            if prv:
                if os.path.exists(cfg):
                    os.remove(cfg)
            else:
                self._write_config(reg,
                                   owner = None, private = False, file = cfg)

        if locale == None:
            locale = self.default_locale

            reg.select_locale(locale)

        # FIXME select highest level found in settings for return
        # FIXME: vpm needs reload/restart indication

        res = self._marshal(reg)
        
        return res

    # FIXME install/remove: improve transactionality
    def install(self, owner, settings, files = None, locale = None):
        self.install_files(owner, files, locale)

        return self.update(owner, settings, locale)
    
    def remove(self, owner, locale = None):
        res = self.update(owner, '', locale)

        self.remove_files(owner, locale)

        return res
            
    # WARNING: resets the registry to the state defined by the
    # maintainer. For maintainer use only. Don't try at home.
    def reset(self, options, settings, file = None):
        r = self._new_registry()
        o = s = None

        o = self._load_file(options, r)
        if o:
            r.reset_options(o.options)

        s = self._load_file(settings, r)
        if s:
            r.reset_configuration(s.settings)

        self._dump_data(r, self.__REGISTRY_DB_PATH)

        return self._write_config(r,
                                  owner = None, private = False, file = file)

    def init(self, options, settings):
        self.reset(options, settings)

    def reinit(self, options, settings):
        self.reset(options, settings)
    
    def get_log_files(self, app_name):
        log_files = []
        return log_files
   
    def get_logrotate_template(self):
        return None
 
    def copy_default_files(self, dest_dir):

        # FIXME: Adding the cartridge name at the end of both the 
        # source and destination directories - this is a WORKAROUND
        # we should use the get_setup_directory and get_scaffolding_directory
        # APIs for the source and destination
        default_dir = os.path.join(self.root, self.META_DIR_NAME , "defaults", os.path.basename(self.root))
        dest_dir = os.path.join(dest_dir, os.path.basename(self.root))
        if os.path.exists(default_dir):
            copy_dir(default_dir, dest_dir)
        
    
def copy_dir(src_dir, dest_dir):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    for file in os.listdir(src_dir):
        src_path = os.path.join(src_dir, file)
        dest_path = os.path.join(dest_dir, file)
        if not os.path.isdir(src_path):
            shutil.copy(src_path, dest_path)
        else:
            copy_dir(src_path, dest_path)

#
# EOF
