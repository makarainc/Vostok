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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/001-install-filemodes.py $
# $Date: 2010-05-16 13:49:52 +0200 (So, 16 Mai 2010) $
# $Revision: 7399 $

import VPM
import unittest
import simplejson
import stat
import os

from utils import *

class TestInstall(unittest.TestCase):

    def setUp(self):
        self.testfolder = 'foo-test'
        
        rm_rf('/tmp/vpm')
        rm_rf(self.testfolder)
        
        ctrl = ControlFile()
        ctrl.settings['Name'] = 'foo'
        ctrl.settings['Version'] = '2.0.0'
        ctrl.settings['Type'] = 'Cartridge'
        ctrl.settings['Provides'] = 'foobar (3.0.0)'
        ctrl.settings['Bundles'] = 'foobar'

        make_vpm(self.testfolder, ctrl)
        
        filemodes = [
                     {
                      "path" : "package-file",
                      "mode" : "0755"}
                     ]
        
        file = os.path.join(self.testfolder,VPM.META_DIR_NAME,VPM.FILEMODE_FILE_NAME)
        fp = open(file, 'w')
        simplejson.dump(filemodes, fp)
        fp.close()
        
        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        r, self.v, e = self.p.pack(self.testfolder, '.')
        self.vpmfile = self.v

    def tearDown(self):
        rm_rf(self.vpmfile)
        
        rm_rf(self.testfolder)

        rm_rf(self.env.install_root)  

    def testInstall(self):
        res, val, err = self.p.install(self.vpmfile, None, VPM.DEPLOY_MODE_MANUAL)

        filestat = os.stat('/tmp/vpm/opt/vostok/cartridges/foo/bundle/package-file')
        mode = filestat[stat.ST_MODE]
        realmode = oct(mode & 0777)

        self.assertEqual(realmode, '0755')

if __name__ == '__main__':
    unittest.main()

#
# EOF
