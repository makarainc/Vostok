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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/cartridge-support/test/info/configuration/configure.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

from glob import glob
import imp
import os.path
import re
import shutil
import subprocess
import sys

from Cartridge.Config import Config


PRINT_WIDTH = 60

class Configuration (Config):
    default_locale = 'en_US'
    conf_dir       = None
    private_config = True

    def __init__(self, root):
        Config.__init__(self, root)
    
    @staticmethod
    def format_item(level, name, params):
        return "%s%-12s: %s\n" % \
               ('  ' * level, name, ' '.join(map(str, params)))

    @staticmethod
    def format_group(level, name, params, format_content):
        v = len(params) > 1 and ' '.join(map(str, params)) or ''
        s = "%s# %s %s" % ('  ' * level, name, v)

        s = "\n" + s + (' -' * (max(PRINT_WIDTH - len(s), 0) / 2)) + "\n"
        s += format_content(level + 1)
        s += "\n"

        return s

    @staticmethod
    def format_scope(level, name, params, format_content):
        s = "\n"
        
        s += "%s%s: %s {\n" % \
            ('  ' * level, name, ' '.join(map(str, params)))
        s += format_content(level + 1)
        s += "%s}\n" % ('  ' * level)
        s += "\n"

        return s


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Testing
#

if __name__ == '__main__':
    import sys
    
    r = os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), '..', '..'))
    c = Configuration(r)
    s = os.path.join(c.CFG_DIR_PATH, 'settings.py')
    o = os.path.join(c.CFG_DIR_PATH, 'options.py')
    p = os.path.join(r, 'test.cfg')
    
    def reset(options = o, settings = s, out = p):
        c.reset(options, settings, out)

    def update(owner, settings):
        f = open(settings, 'r')
        data = ''

        if f:
            try:
                data += f.read()
            finally:
                f.close()
        else:
            sys.stderr.write("Warning: failed to open '%s'" % settings)
        
        return c.update(owner, data)
    
    def get(locale = None, level = c.NORMAL):
        return c.get(locale, level)

    def show(level = c.NORMAL):
        return c.show(c.get(level = level)).to_string()

    debug = False

    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        debug = True
        sys.argv.pop(1)

    if debug:
        import pdb

        if len(sys.argv) == 1:          # run all tests
            pdb.run('reset()')
            pdb.run('update("foo", s)')
            pdb.run('get(level = c.EXPERT)')
            print pdb.run('show(c.EXPERT)')
        else:
            print pdb.run(sys.argv[1])
    else:
        if len(sys.argv) == 1:          # run all tests
            reset()
            update('foo', s)
            get(level = c.EXPERT)
            print show(c.EXPERT)
        else:
            exec(sys.argv[1])

#
# EOF
