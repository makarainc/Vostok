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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/004-install-hooks-error.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestInstallHookError(unittest.TestCase):

    testname = 'InstallHookError'

    def setUp(self):
        ctrl_d = ControlFile()
        ctrl_d.settings['Name'] = self.testname

        self.testfolder = self.testname

        hook_d = HookScript()
        hook_d.set_mode(VPM.POST_INSTALL_NAME, HookScript.FAIL)

        make_vpm(self.testfolder, ctrl_d, hook_d)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v, e = self.p.pack(self.testfolder, '.')

        self.vpmfile = self.v

    def tearDown(self):
        rm_rf(self.vpmfile)
        rm_rf(self.testfolder)

        rm_rf(self.env.install_root)

    def testHookError(self):
        res, val, err = self.p.install(self.vpmfile)

        #self.assertFalse(res)
        #self.assertNotEqual(err, None)

        #self.assertEqual(VPM.DB.UNKNOWN, self.p.db().status(self.testname))

if __name__ == '__main__':
    unittest.main()

#
# EOF
