# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/translators/Translators/PHP.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

import re
from Translators import Translator

class PHP(Translator):
    '''
    PHP config translator
    '''

    #
    # From the Official php.ini:
    #
    #   The syntax of the file is extremely simple.  Whitespace and Lines
    #   beginning with a semicolon are silently ignored (as you probably
    #   guessed).  Section headers (e.g. [Foo]) are also silently ignored, even
    #   though they might mean something in the future.
    #   
    #   Directives are specified using the following syntax: directive = value
    #   Directive names are *case sensitive* - foo=bar is different from
    #   FOO=bar.
    #   
    #   The value can be a string, a number, a PHP constant (e.g. E_ALL or
    #   M_PI), one of the INI constants (On, Off, True, False, Yes, No and None)
    #   or an expression (e.g. E_ALL & ~E_NOTICE), or a quoted string ("foo").
    #   
    #   Expressions in the INI file are limited to bitwise operators and
    #   parentheses:
    #   
    #   |        bitwise OR
    #   &        bitwise AND
    #   ~        bitwise NOT
    #   !        boolean NOT
    #   
    #   Boolean flags can be turned on using the values 1, On, True or Yes.
    #   They can be turned off using the values 0, Off, False or No.
    #   
    #   An empty string can be denoted by simply not writing anything after the
    #   equal sign, or by using the None keyword:
    #   
    #    foo =         ; sets foo to an empty string
    #    foo = none    ; sets foo to an empty string
    #    foo = "none"  ; sets foo to the string 'none'
    #   
    #   If you use constants in your value, and these constants belong to a
    #   dynamically loaded extension (either a PHP extension or a Zend
    #   extension), you may only use these constants *after* the line that loads
    #   the extension.

    # LACUNAE
    #
    #   See http://bugs.php.net/bug.php?id=47703

    #
    # TODO
    #
    #   - flesh out validate() as we see fit. see also case 612

    INIKEY = r'^[_a-zA-Z\x7f-\xff][_a-zA-Z\x7f-\xff\d.]*$'
    INIVAL = '(?:"(?:\\"|[^"])*"|(?:\\.|[^";]))*'

    def _do_line(self, line):
        # (there are no continuation lines in PHP.ini files (I think!)

        # skip empty lines, section headers, and comments
        m = re.match(r'^\s*(?:[;#].*|\[.*\]\s*)?$', line)
        if m:
            return

        # parse remaining lines as directives

        m = re.match(r'^\s*(.*?)\s*=\s*(.*\S)?\s*$', line)
        if not m:
            self.warn("ignoring bogus line '%s'\n" % line);
        else:
            key = m.group(1)
            val = m.group(2)
            
            m = re.match(self.INIKEY, key)
            if not m:
                self.warn("bogus key '%s' in '%s'. Ignoring line.\n" % 
                          (key, line.strip()))
            else:
                m = re.match(r'^(' + self.INIVAL + ')', str(val))
                if not m:
                    self.warn("bogus value '%s' in '%s'. Ignoring line.\n" %
                              (val, line.strip()))
                else:
                    val = m.group(0).strip()

                    if self.validate(key, val):
                        self.out("i('%s', '%s')," % (key, val))

        return

    def run_translation(self, data):
        self.out(self.PREAMBLE)

        if isinstance(data, file):
            for line in data:
                self._do_line(line)
        else:
            for line in data.splitlines():
                self._do_line(line)

        self.out(self.POSTAMBLE)

        return True

#
# EOF
