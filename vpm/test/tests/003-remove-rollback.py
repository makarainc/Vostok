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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/003-remove-rollback.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestRemoveRollback(unittest.TestCase):
    '''
    Error case package removal (no purge)
    Simulate error in hook script to test rollback
    
    Expected outcome: Package A installed
    '''

    test = 'Software'

    def setUp(self):
        ctrl_d1 = ControlFile()
        ctrl_d1.settings['Name'] = self.test

        hook_d = HookScript()
        hook_d.set_modes(HookScript.SUCCEED)
        hook_d.set_mode(VPM.PRE_REMOVE_NAME, HookScript.FAIL)

        make_vpm(self.test, ctrl_d1, hook_d)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v, e = self.p.pack(self.test, '.')
        self.vpmfile = self.v

        res, val, err = self.p.install(self.vpmfile)        

    def tearDown(self):
        rm_rf(self.test)
        rm_rf(self.vpmfile)

        rm_rf(self.env.install_root)

    def testRemoveRollback(self):
        # check if setUp did not fail      
        self.assertEqual(VPM.DB.INSTALLED, self.p.db().status(self.test))
        db = self.p.db()._read_db()

        #remove package
        res, val, err = self.p.remove(self.test)

        # check upgrade results
        self.assertFalse(res)
        self.assertNotEqual(err, None)
        self.assertEqual(VPM.DB.RESOLVED, self.p.db().status(self.test))
        
        check_db = self.p.db()._read_db()
        self.assertEquals(db, check_db)

if __name__ == '__main__':
    unittest.main()

#
# EOF
