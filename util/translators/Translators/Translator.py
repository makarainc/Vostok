# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/translators/Translators/Translator.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

import sys, os

import Cartridge.Config
from Cartridge.Registry import NORMAL, ADVANCED, EXPERT

class TranslatorException(Exception):
    pass

class Config(object):
    LEVELS = {'normal'   : NORMAL,
              'advanced' : ADVANCED,
              'expert'   : EXPERT}

    level          = None
    locale         = None
    cartridge      = None
    registry       = None
    options        = None
    default_locale = None
    
    def __init__(self, **options):
        for key in options.keys():
            if key is 'level':
                if options[key] is None:
                    pass                # will be fixed below
                elif options[key] in self.LEVELS:
                    self.level = self.LEVELS[options[key]]
                else:
                    raise TranslatorException("bad level: '%s'" % options[key])
            if key is 'locale':
                self.locale = options[key]
            if key is 'cartridge':
                self.cartridge = options[key]
            if key is 'registry':
                self.registry = options[key]
            if key is 'options':
                self.options = options[key]
            if key is 'default_locale':
                self.default_locale = options[key]

        # Fixups
        if self.level is None:
            self.level = EXPERT         # FIXME ideally should be NORMAL

        # Options            
        if ((not self.cartridge and not self.registry and not self.options) or 
            (self.cartridge and (self.registry or self.options)) or
            (self.registry and self.options) or
            (self.options and not self.default_locale)):
                raise TranslatorException("a cartridge root directory, " +
                                          "registry file, or options db " +
                                          "file are required")
    


class Translator(object):
    '''
    Base class for configuration file translators
    '''

    #
    # Constants
    # ---------    

    PREAMBLE = ("from Cartridge.Registry import " +
                "item as i, group as g, scope as s\n" +
                "\n" +
                "_ = [")
    POSTAMBLE = ("]\n" +
                 "\n" +
                 "settings = _\n")
    ROOT_INDENT = 5                         # column of last line of PREAMBLE

    # class level variables
    config = None

    options = None

    config_file = None

    output = ''
    warnings = ''

    __first_indent = True
    #
    # Output to stdout
    def out(self, string):
        self.output += string

    def warn(self, msg):
        self.warnings += ("Warning: " + msg)

    @staticmethod
    def error(msg):
        sys.stderr.write("Error: " + msg)

    #
    # File sanity

    def chk_fr(self, file):
        if not os.access(file, os.F_OK):
            raise TranslatorException(("File not found: %s\n" % file))
        if not os.access(file, os.R_OK):
            raise TranslatorException(("File not readable: %s\n" % file))

        return True

        #
    # Options construction

    # Locale selection is not straightforward: the default locale is baked into
    # registry.db's but not declared in options.py files. As a result, it must
    # be specified if Options is derived from an options.py file.

    def options_from_cartridge_root(self, cartridge_root, locale, level):
        c = Cartridge.Config.Config(cartridge_root)
        f = c._Config__REGISTRY_DB_PATH
        o = None

        if self.chk_fr(f):
            r = c._load_data(f)
            l = None

            c._check_registry(r)

            if locale:
                l = locale

            r.select_locale(l)
            r.select_level(level)

            o = r.options()

        return o

    def options_from_registry_db(self, registry_db, locale, level):
        c = Cartridge.Config.Config('/dev/null')
        o = None

        if self.chk_fr(registry_db):
            r = c._load_data(registry_db)
            l = None

            c._check_registry(r)

            if locale:
                l = locale

            r.select_locale(l)
            r.select_level(level)

            o = r.options()

        return o

    def options_from_options_py(self, options_py, default_locale, locale, level):
        c = Cartridge.Config.Config('/dev/null')
        o = None

        c.default_locale = default_locale
        if self.chk_fr(options_py):
            r = c._new_registry()
            d = c._load_file(options_py, r)
            if d:
                l = None

                r.reset_options(d.options)
                c._check_registry(r)

                if locale:
                    l = locale

                r.select_locale(l)
                r.select_level(level)

                o = r.options()

        return o

    #
    # Settings indentation    

    def indent(self, level):
        if self.__first_indent:
            self.__first_indent = False
        else:
            self.out(",\n" + (" " * level))

    #
    # Options DB
    
    def load_options(self, config):
        if config.cartridge:
            self.options = self.options_from_cartridge_root(config.cartridge,
                                                            config.locale,
                                                            config.level)
        elif config.registry:
            self.options = self.options_from_registry_db(config.registry,
                                                         config.locale,
                                                         config.level)
        elif config.options:
            self.options = self.options_from_options_py(config.options, 
                                                        config.default_locale,
                                                        config.locale,
                                                        config.level)
        
        if self.options is None:
            raise TranslatorException("failed to load options")


    #
    # API
    # ---

    def translate_data(self, data, params):
        res = False
        err = ''

        try:
            self.load_options(params)
            self.run_translation(data)
                
            if self.output == '':
                res = False
            else:
                res = self.output
                self.output == ''

            err = self.warnings
               
        except TranslatorException, e:
            err += e
        
        return res, err

    def translate_file(self, filename, params):
        res = False
        err = ''

        if not self.chk_fr(filename):
            return False

        try:
            self.load_options(params)
            try:                
                file = open(filename, 'r')
                
                self.run_translation(file)
                if self.output == '':
                    res = False
                else:
                    res = self.output
                    self.output == ''
               
            finally:
                if file:
                    file.close()

            err = self.warnings
        
        except TranslatorException, e:
            err += e        
            
        return res, err

    #
    # Input directive validation
    #
    # 'option' is the directive, 'values' the list of its arguments. Any or all
    # of these may be validated against the corresponding entry from the options
    # database, 'o' (if any).

    def validate(self, option, values):
        rc = True
        o = self.options.find_by_name(option)

        if o:
            pass                       # more sophisticated validations here
        else:
            self.warn("Ignoring unsupported option '%s'\n" % option)
            rc = False

        return rc

    def run_translation(self, file):
        pass
