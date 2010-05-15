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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/023-setupdirectory.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestGetScaffolding(unittest.TestCase):
    '''
    Scaffolding
    '''

    test1 = 'Webserver'
    test2 = 'PHP'
    test3 = 'JAVA'
    test4 = 'App'
    test5 = 'App2'

    env = None
    p = None

    def setUp(self):
        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)

        ctrl_d11 = ControlFile()
        ctrl_d11.settings['Name'] = self.test1
        ctrl_d11.settings['Type'] = 'Cartridge'
        ctrl_d11.settings['Version'] = '5.5.0'
        #ctrl_d1.settings['Depends'] = ''
        ctrl_d11.settings['Provides'] = 'Tomcat, Apache (2.2.0), www-static.apache2'

        make_vpm(self.test1, ctrl_d11, hooks)
        ctrl_d11 = None

        r, self.v1, e = self.p.pack(self.test1, '.')
        self.vpmfile1 = self.v1

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = self.test2
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'
        ctrl_d2.settings['Depends'] = 'Webserver (>= 5) | Apache (>= 2.1)'

        make_vpm(self.test2, ctrl_d2, hooks)

        r, self.v2, e = self.p.pack(self.test2, '.')
        self.vpmfile2 = self.v2

        # grandchild vpm
        ctrl_d3 = ControlFile()
        ctrl_d3.settings['Name'] = self.test3
        ctrl_d3.settings['Type'] = 'Cartridge'
        ctrl_d3.settings['Provides'] = 'JAVA'
        ctrl_d3.settings['Depends'] = 'Tomcat (>= 5.0) | Tomcat (<=6.0)'

        make_vpm(self.test3, ctrl_d3, hooks)

        r, self.v3, e = self.p.pack(self.test3, '.')
        self.vpmfile3 = self.v3

        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = self.test4
        ctrl_d4.settings['Type'] = 'Application'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'Apache (>= 2.1) | nginx (<= 1.0), PHP'

        make_vpm(self.test4, ctrl_d4, hooks)

        r, self.v4, e = self.p.pack(self.test4, '.')
        self.vpmfile4 = self.v4

        # app 2 vpm
        ctrl_d5 = ControlFile()
        ctrl_d5.settings['Name'] = self.test5
        ctrl_d5.settings['Type'] = 'Application'
        ctrl_d5.settings['Provides'] = 'App2'
        ctrl_d5.settings['Depends'] = 'PHP'

        make_vpm(self.test5, ctrl_d5, hooks)

        r, self.v5, e = self.p.pack(self.test5, '.')
        self.vpmfile5 = self.v5

        #install apache
        res1, val1, err1 = self.p.install(self.vpmfile1)

        #install php
        res2, val2, err2 = self.p.install(self.vpmfile2)

        # install java
        res3, val3, err3 = self.p.install(self.vpmfile3)

        #install app
        res4, val4, err4 = self.p.install(self.vpmfile4)

        res5, val5, errr5 = self.p.install(self.vpmfile5)

    def tearDown(self):
        rm_rf(self.vpmfile1)
        rm_rf(self.test1)

        rm_rf(self.vpmfile2)
        rm_rf(self.test2)

        rm_rf(self.vpmfile3)
        rm_rf(self.test3)

        rm_rf(self.vpmfile4)
        rm_rf(self.test4)

        rm_rf(self.vpmfile5)
        rm_rf(self.test5)

        rm_rf(self.env.install_root)

        rm_rf(self.env.install_root)

    def testGetSetupDirectory(self):
        res, val, err = self.p.get_setup_directory('App2', 'PHP', True)

        self.assertEqual(res, True)
        self.assertEquals(val, ['/tmp/vpm/srv/web-apps/App2/info/setup/PHP', False])
        self.assertEqual(err, None)

    def testGetSetupDirectory2(self):
        cinfo = {'Description': 'Dummy',
                 'Quoted-Name': 'appOne',
                 'Quoted-Version': '1.0.0',
                 'Depends': [
                    [{'Predicate': None, 'Name': 'www-static.apache2', 'String': 'www-static.apache2'}],
                    [{'Name': u'jdk5-1.5.0', 'String': u'jdk5-1.5.0'}]
                    ],
                 'Version': '1.0.0',
                 'Role': 'application',
                 'Architecture': 'all',
                 'Provides': [
                    {'Version': '1.0.0', 'Name': 'appOne', 'String': 'appOne (1.0.0)'}
                    ],
                'Type': 'Application',
                'Name': 'appOne'
        }
        
        self.p.set_control_info(cinfo, '/dev/null')
        
        pkgname = 'appOne'
        dep = [{'Predicate': None, 'Name': 'www-static.apache2', 'String': 'www-static.apache2'}]
        
        res, val, err = self.p.get_setup_directory(pkgname, dep, False)
        
        #print res, val, err

        #self.assertEqual(res, True)
        #self.assertEquals(val, ['/tmp/vpm/srv/web-apps/App3/info/setup/PHP', False])
        #self.assertEqual(err, None)
    
if __name__ == '__main__':
    unittest.main()

#
# EOF
