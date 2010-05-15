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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/009-install-conflict1.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestInstallConflict(unittest.TestCase):
    '''
    Error case 2: dependency chain broken
    
    Expected outcome: all packages installed, dependees not configured    
    '''

    test1 = 'Child1'
    test2 = 'Child2'

    def setUp(self):

        # child vpm
        ctrl_d1 = ControlFile()
        ctrl_d1.settings['Name'] = self.test1
        ctrl_d1.settings['Provides'] = 'Child1'
        ctrl_d1.settings['Conflicts'] = 'Child2'

        make_vpm(self.test1, ctrl_d1)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v1, e = self.p.pack(self.test1, '.')
        self.vpmfile1 = self.v1

        # grandchild vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = self.test2
        ctrl_d2.settings['Provides'] = 'Child2'
        ctrl_d2.settings['Conflicts'] = 'Child1'

        make_vpm(self.test2, ctrl_d2)

        r, self.v2, e = self.p.pack(self.test2, '.')
        self.vpmfile2 = self.v2

    def tearDown(self):
        rm_rf(self.vpmfile1)
        rm_rf(self.test1)

        rm_rf(self.vpmfile2)
        rm_rf(self.test2)

        rm_rf(self.env.install_root)

    def testConflict(self):
        res1, val1, err1 = self.p.install(self.vpmfile1)

        res2, val2, err2 = self.p.install(self.vpmfile2)

        # check first package
        self.assertTrue(res1)
        self.assertEqual(err1, None)
        self.assertEqual(VPM.DB.INSTALLED, self.p.db().status(self.test1))

        # check second package
        self.assertTrue(res2)
        self.assertEqual(err2, None)
        self.assertEqual(VPM.DB.BROKEN, self.p.db().status(self.test2))

if __name__ == '__main__':
    unittest.main()

#
# EOF
