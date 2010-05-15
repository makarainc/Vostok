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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/022-scaffolding3.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import VPM
import unittest

from utils import *

class TestGetScaffolding(unittest.TestCase):
    '''
    Scaffolding
    '''

    test1 = 'Webserver'

    env = None
    p = None

    def setUp(self):
        
        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)

        ctrl_d1 = ControlFile()
        ctrl_d1.settings['Name'] = self.test1
        ctrl_d1.settings['Type'] = 'Cartridge'
        ctrl_d1.settings['Version'] = '5.5.0'
        ctrl_d1.settings['Provides'] = 'Tomcat, Apache (2.2.0)'

        make_vpm(self.test1, ctrl_d1, hooks)

        r, self.v1, e = self.p.pack(self.test1, '.')
        self.vpmfile1 = self.v1

        #install apache
        res1, val1, err1 = self.p.install(self.vpmfile1)

    def tearDown(self):
        rm_rf(self.vpmfile1)
        rm_rf(self.test1)

        rm_rf(self.env.install_root)

    def testGetScaffoldingVirtualDT3(self):
        cdata = """Name: App3
Version: 1.0.0
Architecture: all
Provides: App3
Depends: Tomcat
Type: Application"""
    
        # <none> means memory    
        info = VPM.ControlInfo(cdata, '<none>')    
        
        self.p.set_control_info(info, '/dev/null')

        # prepare dependency
        dep = [{'Predicate': None, 'Name': 'Tomcat', 'String': 'Tomcat'}]

        # scaffolding
        res, val, err = self.p.get_scaffolding(None, dep, 'App3')

        #scaffolding_test = [{'Status': 'resolved', 'Vendor': '', 'Name': 'PHP','Install-Root': '/tmp/vpm/opt/vostok/cartridges','Quoted-Name': 'PHP', 'Install-Name': 'PHP','Bundles': '', 'Quoted-Version': '5.5.0','Description': '', 'Build': '1', 'Depends': [[{'Predicate': "lambda v: v >= '5'", 'Name': 'Webserver', 'String': 'Webserver (>= 5)'}, {'Predicate': "lambda v: v >= '2.1'", 'Name': 'Apache', 'String': 'Apache (>= 2.1)'}]], 'Version': '5.5.0', 'Role': 'application', 'Package-State': 'Virgin', 'Provides': [{'Version': '5.5.0', 'Name': 'PHP', 'String': 'PHP (5.5.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Cartridge', 'Architecture': 'all'},None,None]
        
        self.assertEqual(res, True)
        #self.assertEquals(scaffolding_test, val)
        self.assertEqual(err, None)
        
        ## Test removal
        res, val, err = self.p.info('App3')
        if res and val != None:        
            app3_r, app3_v, app3_e = self.p.remove('App3', VPM.DEPLOY_MODE_MANUAL)
            
            print app3_r, app3_v, app3_e
            
            self.assertEqual(app3_r, True)
            
            db = self.p.db()._read_db()
    
            check_db = {
                'Webserver': {'Status': 'committed', 'Vendor': '', 'Name': 'Webserver', 'Install-Root': '/tmp/vpm/opt/vostok/cartridges', 'Install-Name': 'Webserver', 'Quoted-Name': 'Webserver', 'Bundles': '', 'Quoted-Version': '5.5.0', 'Package-State': 'Virgin', 'Architecture': 'all', 'Depends': [[{'Predicate': None, 'Name': 'PHP', 'String': 'PHP'}]], 'Version': '5.5.0', 'Role': 'application', 'Build': '1', 'Provides': [{'Version': '5.5.0', 'Name': 'Webserver', 'String': 'Webserver (5.5.0)'}, {'Version': '5.5.0', 'Name': 'Tomcat', 'String': 'Tomcat (5.5.0)'}, {'Version': '2.2.0', 'Name': 'Apache', 'String': 'Apache (2.2.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Cartridge', 'Description': ''}
                }
            #self.assertEquals(db, check_db)
            tmp = db.get('App3', None)
            self.assertEquals(tmp, None)
                 
if __name__ == '__main__':
    unittest.main()

#
# EOF
