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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/004-remove-dependency-table-complex.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestDependencyTableComplexRemove(unittest.TestCase):
    '''
    Removal. Dependency table not modified because package is not removable 
    '''

    test1 = 'Webserver'
    test2 = 'Apache'
    test3 = 'PHP'

    def setUp(self):
        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)
        
        ctrl_d1 = ControlFile()
        ctrl_d1.settings['Name'] = self.test1
        ctrl_d1.settings['Type'] = 'Cartridge'
        ctrl_d1.settings['Version'] = '1.0.0'
        ctrl_d1.settings['Provides'] = 'Webserver'

        make_vpm(self.test1, ctrl_d1, hooks)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v1, e = self.p.pack(self.test1, '.')
        self.vpmfile1 = self.v1

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = self.test2
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'Apache'
        ctrl_d1.settings['Version'] = '2.2.3'

        make_vpm(self.test2, ctrl_d2, hooks)

        r, self.v2, e = self.p.pack(self.test2, '.')
        self.vpmfile2 = self.v2

        # grandchild vpm
        ctrl_d3 = ControlFile()
        ctrl_d3.settings['Name'] = self.test3
        ctrl_d3.settings['Type'] = 'Cartridge'
        ctrl_d3.settings['Provides'] = 'php'
        ctrl_d3.settings['Depends'] = 'Webserver (<= 1.5.0) | Apache (>= 2.0)'

        make_vpm(self.test3, ctrl_d3, hooks)

        r, self.v3, e = self.p.pack(self.test3, '.')
        self.vpmfile3 = self.v3

        self.p.install(self.vpmfile1)

        #install php
        self.p.install(self.vpmfile2)

        #install java
        self.p.install(self.vpmfile3)

    def tearDown(self):
        rm_rf(self.vpmfile1)
        rm_rf(self.test1)

        rm_rf(self.vpmfile2)
        rm_rf(self.test2)

        rm_rf(self.vpmfile3)
        rm_rf(self.test3)

        rm_rf(self.env.install_root)

    def testDependencyTableComplexRemove(self):
        # check first package        
        check_dt = {'PHP': [{'feature': 
                [{'Predicate': "lambda v: v <= '1.5.0'", 'Name': 'Webserver', 'String': 'Webserver (<= 1.5.0)'},
                  {'Predicate': "lambda v: v >= '2.0'", 'Name': 'Apache', 'String': 'Apache (>= 2.0)'}], 
                  'provider': {'sel-feature': 'Webserver', 'Version': '1.0.0', 'Name': 'Webserver'},
                  'virtual' : False}], 
            }

        dt = self.p.db()._read_dt_db()
        self.assertEqual(dt, check_dt)

        # remove packages
        res, val, err = self.p.remove(self.test1)

        self.assertTrue(res)
        self.assertEqual(err, None)
        #self.assertEqual(VPM.DB.RESOLVED, self.p.db().status(self.test1))

        dt = self.p.db()._read_dt_db()
        
        check_dt2 = {'PHP': [{'feature': 
                [{'Predicate': "lambda v: v <= '1.5.0'", 'Name': 'Webserver', 'String': 'Webserver (<= 1.5.0)'},
                  {'Predicate': "lambda v: v >= '2.0'", 'Name': 'Apache', 'String': 'Apache (>= 2.0)'}], 
                  'provider': {'sel-feature': 'Apache', 'Version': '2.2.3', 'Name': 'Apache'},
                  'virtual' : False}], 
            }
        
        self.assertEqual(dt, check_dt2)

if __name__ == '__main__':
    unittest.main()

#
# EOF
