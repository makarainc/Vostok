# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/translators/Translators/Apache.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

import re
from Translators import Translator

class Apache(Translator):
    '''
    Apache config translator
    '''

    #
    # From the Apache Documentation:
    #
    #   Syntax of the Configuration  Files
    #   ----------------------------------
    #
    #   Apache configuration files contain one directive per line. The
    #   back-slash "\" may be used as the last character on a line to indicate
    #   that the directive continues onto the next line. There must be no other
    #   characters or white space between the back-slash and the end of the
    #   line.
    #
    #   Directives in the configuration files are case-insensitive, but
    #   arguments to directives are often case sensitive. Lines which begin with
    #   the hash character "#" are considered comments, and are
    #   ignored. Comments may not be included on a line after a configuration
    #   directive. Blank lines and white space occurring before a directive are
    #   ignored, so you may indent directives for clarity.

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

        # check for scope directives upfront
        m = re.match(r'^\s*<\s*(/)?\s*(.*\S)\s*>\s*$', line)
        if m:
            if m.group(1):              # end scope
                state['end'] = True
            else:                       # begin scope
                state['beg'] = True
            line = m.group(2)           # drop angle brackets

        # FIXME the \\" regex part works but is not generally correct
        m = re.findall(r'("(?:\\"|[^"])+"|(?:\\.|\S)+)', line)
        if m:
            o = m[0]

            if self.validate(o, m[1:]):
                if state['beg']:
                    state['beg'] = False
                    self.indent(state['ind'])
                    self.out("s(('%s'" % o)
                    state['ind'] += 2
                elif state['end']:
                    state['end'] = False
                    self.out(")")
                    state['ind'] -= 2
                    return              # don't print another closing paren
                else:
                    self.indent(state['ind'])
                    self.out("i('%s'" % o)

                for v in m[1:]:
                    if v[0] == '"':
                        # for some reason backslashes in strings (e.g. LogFormat
                        # arguments) must be escaped. this is ugly of course.
                        v = re.sub(r'([^\\])\\"', r'\1\\\\"', v)

                    self.out(", '%s'" % v)

                self.out(")")

            return

        else:
            self.warn("ignoring bogus line '%s'\n", line);

    def run_translation(self, data):
        state = {'ind'  : self.ROOT_INDENT,
                 'head' : '',
                 'beg'  : False,
                 'end'  : False}

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
