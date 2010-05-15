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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/001-install.py $
# $Date: 2010-05-15 21:40:49 +0200 (Sa, 15 Mai 2010) $
# $Revision: 7394 $

import VPM
import unittest

from utils import *

class TestInstall(unittest.TestCase):

    def setUp(self):
        self.testfolder = 'foo-test'
        self.testfolder2= 'foo-test2'
        
        rm_rf('/tmp/vpm')
        rm_rf(self.testfolder)
        rm_rf(self.testfolder2)
        
        ctrl = ControlFile()
        ctrl.settings['Name'] = 'foo'
        ctrl.settings['Version'] = '2.0.0'
        ctrl.settings['Type'] = 'Cartridge'
        ctrl.settings['Provides'] = 'foobar (3.0.0)'
        ctrl.settings['Bundles'] = 'foobar'

        make_vpm(self.testfolder, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v, e = self.p.pack(self.testfolder, '.')

        self.vpmfile = self.v
        
        ctrl2 = ControlFile()
        ctrl2.settings['Name'] = 'foo2'
        ctrl2.settings['Type'] = 'Cartridge'
        ctrl2.settings['Depends'] = 'foobar (>= 2.0)'

        make_vpm(self.testfolder2, ctrl2)

        r, self.v, e = self.p.pack(self.testfolder2, '.')

        self.vpmfile2 = self.v

    def tearDown(self):
        rm_rf(self.vpmfile)
        rm_rf(self.vpmfile2)
        
        rm_rf(self.testfolder)
        rm_rf(self.testfolder2)

        rm_rf(self.env.install_root)  

    def testInstall(self):
        res, val, err = self.p.install(self.vpmfile, None, VPM.DEPLOY_MODE_MANUAL)

        self.assertTrue(res)
        self.assertEqual(err, None)
        
        res, val, err = self.p.install(self.vpmfile2, None, VPM.DEPLOY_MODE_MANUAL)

        self.assertTrue(res)
        self.assertEqual(err, None)

if __name__ == '__main__':
    unittest.main()

#
# EOF
