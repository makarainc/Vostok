'''
Created on 15.04.2010

@author: cmk
'''
import unittest
import re

import VPM

class Test(unittest.TestCase):

    def _parse_declarations(self, lines, pathname):
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
                        raise ValueError("%s: line %d malformed: '%s'" \
                                               % (pathname, n, l))

        return d

    def testControlInfo(self):
        cfile = 'control'
        bfile = 'build'
        
        cdata = """Name: test-php52
Version: 1.0.0
Architecture: all
Provides: 
Depends: www-static.apache2, www-dynamic.apache2, php-5.2.10
Description: Minimal scaffolding. This application does not yet depend on any support cartridges other than the (required) static Apache cartridge.
Delegate: php-5.2.10
Type: Application
Role: application
"""
        
        bdata = """Build: 1
        """

        cinfo = self._parse_declarations(cdata.splitlines(), cfile)
        binfo = self._parse_declarations(bdata.splitlines(), bfile)

        info = VPM.ControlInfo(cinfo, cfile)

        #info.setBuildInfo(binfo)
        
        self.assertEquals(cdata, info.toString())

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testControlInfo']
    unittest.main()