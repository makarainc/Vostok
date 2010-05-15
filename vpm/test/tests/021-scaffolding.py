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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/021-scaffolding.py $
# $Date: 2010-03-31 02:42:32 +0200 (Mi, 31 Mrz 2010) $
# $Revision: 6415 $

import VPM
import unittest

from utils import *

class TestGetScaffolding(unittest.TestCase):
    '''
    Scaffolding
    '''
    
    def setUp(self):
        self.env = VPM.Environment('/tmp/vpm')
        #self.p = VPM.Package(self.env)

    def tearDown(self):        
        rm_rf(self.env.install_root)

    def testGetScaffolding1(self):
        dt = {'A1': [{'feature':[{'Name':'F1','Predicate':None,'String':'F1'},{'Name':'F2','Predicate':None,'String':'F2'}], 'provider' : {'Name':'C1','Version':'1.0'} },
                     {'feature':[{'Name':'F3','Predicate':None,'String':'F3'}], 'provider' : {'Name':'C2','Version':'1.0'} }],
              'A2': [{'feature':[{'Name':'F1','Predicate':None,'String':'F1'}], 'provider' : {'Name':'C3','Version':'2.0'} }]}
        
        db = VPM.DB(self.env)
        
        dependency = [{'Name':'F1','Predicate':None,'String':'F1'},{'Name':'F2','Predicate':None,'String':'F2'}]
        dependant = 'A1'
        
        prov = None
        for dep in dependency:
            # search provider for p
            tmp = db._dt_search_features_by_pkg(dt, dependant, dep['Name'])
            
            if prov is None:
                prov = tmp['Name']
            else:
                if tmp['Name'] == prov:
                    # Or relation found
                    break
                else:
                    print "Invalid dependency structure"
        
        self.assertEquals(prov,'C1')
    
    def testGetScaffolding2(self):
        dt = {'A1': [{'feature':[{'Name':'F1','Predicate':None,'String':'F1'},{'Name':'F2','Predicate':None,'String':'F2'}], 'provider' : {'Name':'C1','Version':'1.0'} },
                     {'feature':[{'Name':'F3','Predicate':None,'String':'F3'}], 'provider' : {'Name':'C2','Version':'1.0'} }],
              'A2': [{'feature':[{'Name':'F1','Predicate':None,'String':'F1'}], 'provider' : {'Name':'C3','Version':'2.0'} }]}
        
        db = VPM.DB(self.env)
        
        dependency = [{'Name':'F1','Predicate':None,'String':'F1'}]
        dependant = 'A2'
        
        prov = None
        for dep in dependency:
            # search provider for p
            tmp = db._dt_search_features_by_pkg(dt, dependant, dep['Name'])
            
            if prov is None:
                prov = tmp['Name']
            else:
                if tmp['Name'] == prov:
                    # Or relation found
                    break
                else:
                    print "Invalid dependency structure"
        
        self.assertEquals(prov,'C3')

if __name__ == '__main__':
    unittest.main()

#
# EOF
