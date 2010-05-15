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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/001-dependency-chain.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import sys
import unittest

from utils import *

class TestDependChainResolver(unittest.TestCase):

    def setUp(self):
        self.db = {}
        self.env = VPM.Environment('/tmp/vpm')

    def tearDown(self):
        rm_rf(self.env.install_root)

    def testChainResolver(self):
        pass
#        t = os.path.join(os.getcwd(), sys.argv[0])
#
#        f = os.path.join(os.path.dirname(t), 'data', 'db')
#
#        self.db = eval(read_file(f))
#
#        pdb = VPM.DB(self.env)
#
#        print self.db
#        
#        deps = self.db['php-5.2.10'].Depends
#
#        deps.reverse()
#
#        chain = pdb._resolve_depends_chain('php-5.2.10', self.db)
#
#        testchain = ['www-dynamic.apache2', 'www-static.apache2']
#        self.assertEquals(chain, testchain)

if __name__ == '__main__':
    unittest.main()

#
# EOF
