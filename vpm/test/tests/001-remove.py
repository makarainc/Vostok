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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/001-remove.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestRemove(unittest.TestCase):
    '''
    Standard case package removal (no purge)
    
    Expected outcome: Package A removed
    '''

    test = 'Software'

    def setUp(self):
        ctrl_d1 = ControlFile()
        ctrl_d1.settings['Name'] = self.test

        hook_d = HookScript()
        hook_d.set_modes(HookScript.SUCCEED)
        
        make_vpm(self.test, ctrl_d1, hook_d)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v, e = self.p.pack(self.test, '.')
        self.vpmfile = self.v

        res, val, err = self.p.install(self.vpmfile)

        rm_rf(self.test)

    def tearDown(self):
        rm_rf(self.vpmfile)

        rm_rf(self.env.install_root)

    def testRemove(self):
        # check if setUp did not fail      
        self.assertEqual(VPM.DB.INSTALLED, self.p.db().status(self.test))

        #remove package
        res, val, err = self.p.remove(self.test)

        # check upgrade results
        self.assertTrue(res)
        self.assertEqual(err, None)
        self.assertEqual(VPM.DB.UNKNOWN, self.p.db().status(self.test))

if __name__ == '__main__':
    unittest.main()

#
# EOF
