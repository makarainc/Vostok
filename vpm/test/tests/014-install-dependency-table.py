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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/014-install-dependency-table.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestDependencyTableSimple(unittest.TestCase):
    '''
    Simple dependency table 
    '''

    test1 = 'Webserver'
    test2 = 'PHP'
    test3 = 'JAVA'

    def setUp(self):
        ctrl_d1 = ControlFile()
        ctrl_d1.settings['Name'] = self.test1
        ctrl_d1.settings['Type'] = 'Cartridge'
        ctrl_d1.settings['Version'] = '5.5.0'
        ctrl_d1.settings['Provides'] = 'Tomcat, Apache (2.2.0)'

        make_vpm(self.test1, ctrl_d1)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v1, e = self.p.pack(self.test1, '.')
        self.vpmfile1 = self.v1

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = self.test2
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'
        ctrl_d2.settings['Depends'] = 'Webserver (>= 5) | Apache (>= 2.1)'

        make_vpm(self.test2, ctrl_d2)

        r, self.v2, e = self.p.pack(self.test2, '.')
        self.vpmfile2 = self.v2

        # grandchild vpm
        ctrl_d3 = ControlFile()
        ctrl_d3.settings['Name'] = self.test3
        ctrl_d3.settings['Type'] = 'Cartridge'
        ctrl_d3.settings['Provides'] = 'JAVA'
        ctrl_d3.settings['Depends'] = 'Tomcat (>= 5.0) | Tomcat (<=6.0)'

        make_vpm(self.test3, ctrl_d3)

        r, self.v3, e = self.p.pack(self.test3, '.')
        self.vpmfile3 = self.v3

    def tearDown(self):
        rm_rf(self.vpmfile1)
        rm_rf(self.test1)

        rm_rf(self.vpmfile2)
        rm_rf(self.test2)

        rm_rf(self.vpmfile3)
        rm_rf(self.test3)

        rm_rf(self.env.install_root)

    def testDependencyTable(self):
        #install apache
        res1, val1, err1 = self.p.install(self.vpmfile1, None, VPM.DEPLOY_MODE_MANUAL)

        dt = self.p.db().dt()._read_dt_db()
        # check first package
        self.assertTrue(res1)
        self.assertEqual(err1, None)
        self.assertEqual(VPM.DB.RESOLVED, self.p.db().status(self.test1))

        self.assertEqual(dt, {})
        
        #install php
        res2, val2, err2 = self.p.install(self.vpmfile2, None, VPM.DEPLOY_MODE_MANUAL)

        check_dt = {'PHP': 
            [{'feature': [{'Predicate': "lambda v: v >= '5'", 'Name': 'Webserver', 'String': 'Webserver (>= 5)'},
                          {'Predicate': "lambda v: v >= '2.1'", 'Name': 'Apache', 'String': 'Apache (>= 2.1)'}],
              'provider': {'sel-feature': 'Webserver', 'Version': '5.5.0', 'Name': 'Webserver'},
              'virtual': False}]
            }

        # check second package
        self.assertTrue(res2)
        self.assertEqual(err2, None)
        self.assertEqual(VPM.DB.RESOLVED, self.p.db().status(self.test2))

        dt = self.p.db()._read_dt_db()
        self.assertEqual(dt, check_dt)

        # install java
        res3, val3, err3 = self.p.install(self.vpmfile3, None, VPM.DEPLOY_MODE_MANUAL)
        
        #test dual install
        res3, val3, err3 = self.p.install(self.vpmfile3, None, VPM.DEPLOY_MODE_MANUAL)

        # check third package
        self.assertTrue(res3)
        self.assertEqual(err3, None)
        self.assertEqual(VPM.DB.RESOLVED, self.p.db().status(self.test3))

        check_dt = {'PHP': 
            [{'feature': [{'Predicate': "lambda v: v >= '5'", 'Name': 'Webserver', 'String': 'Webserver (>= 5)'},
                          {'Predicate': "lambda v: v >= '2.1'", 'Name': 'Apache', 'String': 'Apache (>= 2.1)'}],
              'provider': {'sel-feature': 'Webserver', 'Version': '5.5.0', 'Name': 'Webserver'},
              'virtual': False}],
              'JAVA': 
              [{'feature': [{'Predicate': "lambda v: v >= '5.0'", 'Name': 'Tomcat', 'String': 'Tomcat (>= 5.0)'},
                            {'Predicate': "lambda v: v <= '6.0'", 'Name': 'Tomcat', 'String': 'Tomcat (<= 6.0)'}],
                'provider': {'sel-feature': 'Tomcat', 'Version': '5.5.0', 'Name': 'Webserver'},
                'virtual': False}]
            }
        
        dt = self.p.db()._read_dt_db()
        self.assertEquals(dt, check_dt)

if __name__ == '__main__':
    unittest.main()

#
# EOF
