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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/020-install-vshome-interpolation.py $
# $Date: 2010-05-15 21:40:49 +0200 (Sa, 15 Mai 2010) $
# $Revision: 7394 $

import VPM
import unittest

from utils import *

class TestVSHomeInterpolation(unittest.TestCase):

    testroot = ''
    
    def setUp(self):
        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)
        
        self.pkgname  = 'test-package'
        self.testroot = os.path.join(self.env.install_root, self.pkgname)
        
        if not os.path.exists(self.testroot):
            os.mkdir('/tmp/vpm')
            os.mkdir(self.testroot)
            os.mkdir(os.path.join(self.testroot, 'settings'))
            
        data = """/foo/bar@VS_HOME/bal/bal
        /foo/bar@{VS_HOME}/bal/bal
        /foo/bar@{%s:VS_HOME}/bal/bal
        /foo/bar@VS_TMP/bal/bal
        /foo/bar@{VS_TMP}/bal/bal
        /foo/bar@{%s:VS_TMP}/bal/bal
        /foo/bar@VS_LOGS/bal/bal
        /foo/bar@{VS_LOGS}/bal/bal
        /foo/bar@{%s:VS_LOGS}/bal/bal
        """ % (self.pkgname, self.pkgname,self.pkgname )
                
        write_file(os.path.join(self.testroot, 'settings', 'settings.conf'), data)

    def tearDown(self):
        rm_rf(self.testroot)

        rm_rf(self.env.install_root)  

    def testInterpolation(self):
        
        self.p._interpolate_vshome(self.pkgname, self.testroot, 'test-package', os.path.join(self.testroot, 'settings'))
        
        test_data = """/foo/bar/tmp/vpm/test-package/bundle/bal/bal
        /foo/bar/tmp/vpm/test-package/bundle/bal/bal
        /foo/bar/tmp/vpm/test-package/bundlebal/bal
        /foo/bar/tmp/vpm/test-package/bundle/.data/tmp/bal/bal
        /foo/bar/tmp/vpm/test-package/bundle/.data/tmp/bal/bal
        /foo/bar/tmp/vpm/test-package/bundle/.data/tmp/bal/bal
        /foo/bar/tmp/vpm/test-package/bundle/.data/logs/bal/bal
        /foo/bar/tmp/vpm/test-package/bundle/.data/logs/bal/bal
        /foo/bar/tmp/vpm/test-package/bundle/.data/logs/bal/bal
        """
                
        data = read_file(os.path.join(self.testroot, 'settings', 'settings.conf'))
        
        print data
        
        self.assertEquals(test_data, data)

if __name__ == '__main__':
    unittest.main()

#
# EOF
