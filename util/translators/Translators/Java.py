# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/translators/Translators/Java.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

import re
from Translators import Translator

class Java(Translator):
    '''
    Java config translator
    '''
    # Java Options only so far. See
    # 
    #   http://java.sun.com/j2se/1.5.0/docs/tooldocs/windows/java.html
    #
    # TODO
    #
    #   - flesh out validate() as we see fit. see also case 612

    def _do_line(self, rawline, state):
        # concatenate line continuations
        m = re.match(r'^(.*)\\$', rawline)
        if m:
            # add space as backslash is whitespace
            state['head'] += m.group(1) + ' '
            return

        if state['head']:
            line = state['head'] + rawline
            state['head'] = ''
        else:
            line = rawline

        # skip empty lines and comments
        m = re.match(r'^\s*(?:#.*)?$', line)
        if m:
            return

        # parse all other lines as directives

        # Let's parse the Java options mess simply. This is not
        # generally correct but should catch most everything:
        #
        #   '-' name {{':' val}* {'=' option}*}?
        #
        # Don't deal with quoted things yet (-Dfoo="a = b")
        m = re.match(r'^\s*(-.*?)(?:((?::[^:]+)*)((?:=[^=]+)*))?\s*$', line)
        if not m:
            self.warn("ignoring bogus line '%s'\n" % line);
            return


        key = m.group(1) 
        sks = m.group(2)            # subkey for lack of a better word
        svs = m.group(3)            # subvalue, ditto

        vals = []

        if sks:
            vals.extend(re.split(r'(:)', sks)[1:])
        if svs:
            vals.extend(re.split(r'(=)', svs)[1:])

        # FIXME: set to validate again once Java cartridges have a full
        # options DB worked out
        if True: # self.validate(key, vals):
            self.indent(state['ind'])
            self.out("i('%s'" % key)

            for v in vals:
                self.out(", '%s'" % v)

            self.out(")")

    def run_translation(self, data):
        state = {'ind'  : self.ROOT_INDENT,
                 'head' : '',
                 'beg'  : False,        # unused
                 'end'  : False}        # unused
        
        self.out(self.PREAMBLE)

        if isinstance(data, file):
            for rawline in data:
                self._do_line(rawline, state)
        else:
            for rawline in data.splitlines():
                self._do_line(rawline, state)

        self.out(self.POSTAMBLE)

        if state['ind'] != self.ROOT_INDENT:
            self.error("unbalanced configuration (nesting level: %d)\n"
                  % int((state['ind'] - self.ROOT_INDENT) / 2))

        return True

#
# EOF
