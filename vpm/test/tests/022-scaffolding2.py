# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/022-scaffolding2.py $
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
    test2 = 'PHP'
    test3 = 'JAVA'
    test4 = 'App'
    test5 = 'App2'

    env = None
    p = None

    def setUp(self):
        self.app3_vpmfile = None
        
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

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = self.test2
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'
        ctrl_d2.settings['Depends'] = 'Webserver (>= 5) | Apache (>= 2.1)'

        make_vpm(self.test2, ctrl_d2, hooks)

        r, self.v2, e = self.p.pack(self.test2, '.')
        self.vpmfile2 = self.v2

        # grandchild vpm
        ctrl_d3 = ControlFile()
        ctrl_d3.settings['Name'] = self.test3
        ctrl_d3.settings['Type'] = 'Cartridge'
        ctrl_d3.settings['Provides'] = 'JAVA'
        ctrl_d3.settings['Depends'] = 'Tomcat (>= 5.0) | Tomcat (<=6.0)'

        make_vpm(self.test3, ctrl_d3, hooks)

        r, self.v3, e = self.p.pack(self.test3, '.')
        self.vpmfile3 = self.v3

        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = self.test4
        ctrl_d4.settings['Type'] = 'Cartridge'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'Apache (>= 2.1) | nginx (<= 1.0), PHP'

        make_vpm(self.test4, ctrl_d4, hooks)

        r, self.v4, e = self.p.pack(self.test4, '.')
        self.vpmfile4 = self.v4

        # app 2 vpm
        ctrl_d5 = ControlFile()
        ctrl_d5.settings['Name'] = self.test5
        ctrl_d5.settings['Type'] = 'Cartridge'
        ctrl_d5.settings['Provides'] = 'App2'
        ctrl_d5.settings['Depends'] = 'PHP'

        make_vpm(self.test5, ctrl_d5, hooks)

        r, self.v5, e = self.p.pack(self.test5, '.')
        self.vpmfile5 = self.v5

        #install apache
        res1, val1, err1 = self.p.install(self.vpmfile1)

        #install php
        res2, val2, err2 = self.p.install(self.vpmfile2)

        # install java
        res3, val3, err3 = self.p.install(self.vpmfile3)

        #install app
        res4, val4, err4 = self.p.install(self.vpmfile4)

        res5, val5, errr5 = self.p.install(self.vpmfile5)

    def tearDown(self):
        rm_rf(self.vpmfile1)
        rm_rf(self.test1)

        rm_rf(self.vpmfile2)
        rm_rf(self.test2)

        rm_rf(self.vpmfile3)
        rm_rf(self.test3)

        rm_rf(self.vpmfile4)
        rm_rf(self.test4)

        rm_rf(self.vpmfile5)
        rm_rf(self.test5)

        rm_rf(self.env.install_root)
        
    def testGetScaffoldingVirtualDT(self):                
        cinfo = {'Description': 'Dummy',
                 'Quoted-Name': 'appOne',
                 'Quoted-Version': '1.0.0',
                 'Depends': [
                    [{'Predicate': None, 'Name': 'www-static.apache2', 'String': 'www-static.apache2'}],
                    [{'Name': u'jdk5-1.5.0', 'String': u'jdk5-1.5.0'}]
                    ],
                 'Version': '1.0.0',
                 'Role': 'application',
                 'Architecture': 'all',
                 'Provides': [
                    {'Version': '1.0.0', 'Name': 'appOne', 'String': 'appOne (1.0.0)'}
                    ],
                'Type': 'Application',
                'Name': 'appOne'
        }
        
        self.p.set_control_info(cinfo, '/dev/null')

        # prepare dependency
        dep = [{'Predicate': None, 'Name': 'PHP', 'String': 'PHP'}]

        # scaffolding
        res, val, err = self.p.get_scaffolding(None, dep, 'App3')

        scaffolding_test = [{'Status': 'resolved', 'Vendor': '', 'Name': 'PHP','Install-Root': '/tmp/vpm/opt/vostok/cartridges','Quoted-Name': 'PHP', 'Install-Name': 'PHP','Bundles': '', 'Quoted-Version': '5.5.0','Description': '', 'Build': '1', 'Depends': [[{'Predicate': "lambda v: v >= '5'", 'Name': 'Webserver', 'String': 'Webserver (>= 5)'}, {'Predicate': "lambda v: v >= '2.1'", 'Name': 'Apache', 'String': 'Apache (>= 2.1)'}]], 'Version': '5.5.0', 'Role': 'application', 'Package-State': 'Virgin', 'Provides': [{'Version': '5.5.0', 'Name': 'PHP', 'String': 'PHP (5.5.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Cartridge', 'Architecture': 'all'},None,None]
        
        #self.assertEqual(res, True)
        #self.assertEquals(scaffolding_test, val)
        #self.assertEqual(err, None)
        
        db = self.p.db()._read_db()
        check_db = {'JAVA': {'Status': 'resolved', 'Vendor': '', 'Name': 'JAVA', 'Install-Root': '/tmp/vpm/opt/vostok/cartridges', 'Install-Name': 'JAVA', 'Quoted-Name': 'JAVA', 'Bundles': '', 'Quoted-Version': '5.5.0', 'Package-State': 'Virgin', 'Architecture': 'all', 'Depends': [[{'Predicate': "lambda v: v >= '5.0'", 'Name': 'Tomcat', 'String': 'Tomcat (>= 5.0)'}, {'Predicate': "lambda v: v <= '6.0'", 'Name': 'Tomcat', 'String': 'Tomcat (<= 6.0)'}]], 'Version': '5.5.0', 'Role': 'application', 'Build': '1', 'Provides': [{'Version': '5.5.0', 'Name': 'JAVA', 'String': 'JAVA (5.5.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Cartridge', 'Description': ''},
                    'App': {'Status': 'resolved', 'Vendor': '', 'Name': 'App', 'Install-Root': '/tmp/vpm/srv/web-apps', 'Install-Name': 'App', 'Quoted-Name': 'App', 'Bundles': '', 'Quoted-Version': '5.5.0', 'Package-State': 'Virgin', 'Architecture': 'all', 'Depends': [[{'Predicate': "lambda v: v >= '2.1'", 'Name': 'Apache', 'String': 'Apache (>= 2.1)'}, {'Predicate': "lambda v: v <= '1.0'", 'Name': 'nginx', 'String': 'nginx (<= 1.0)'}], [{'Predicate': None, 'Name': 'PHP', 'String': 'PHP'}]], 'Version': '5.5.0', 'Role': 'application', 'Build': '1', 'Provides': [{'Version': '5.5.0', 'Name': 'App', 'String': 'App (5.5.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Application', 'Description': ''},                    
                    'App3': {'Vendor': '', 'Name': 'App3', 'Quoted-Name': 'App3', 'Bundles': '', 'Quoted-Version': '1.0.0', 'virtual': True, 'Depends': [[{'Predicate': None, 'Name': 'PHP', 'String': 'PHP'}]], 'Version': '1.0.0', 'Role': 'application', 'Architecture': 'all', 'Provides': [{'Version': '1.0.0', 'Name': 'App3', 'String': 'App3 (1.0.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Application', 'Description': ''},                    
                    'App2': {'Status': 'resolved', 'Vendor': '', 'Name': 'App2', 'Install-Root': '/tmp/vpm/srv/web-apps', 'Install-Name': 'App2', 'Quoted-Name': 'App2', 'Bundles': '', 'Quoted-Version': '5.5.0', 'Package-State': 'Virgin', 'Architecture': 'all', 'Depends': [[{'Predicate': None, 'Name': 'PHP', 'String': 'PHP'}]], 'Version': '5.5.0', 'Role': 'application', 'Build': '1', 'Provides': [{'Version': '5.5.0', 'Name': 'App2', 'String': 'App2 (5.5.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Application', 'Description': ''},
                    'Webserver': {'Status': 'committed', 'Vendor': '', 'Name': 'Webserver', 'Install-Root': '/tmp/vpm/opt/vostok/cartridges', 'Quoted-Name': 'Webserver', 'Install-Name': 'Webserver', 'Bundles': '', 'Quoted-Version': '5.5.0', 'Description': '', 'Build': '1', 'Depends': [[{'Predicate': None, 'Name': 'PHP', 'String': 'PHP'}]], 'Version': '5.5.0', 'Role': 'application', 'Package-State': 'Virgin', 'Provides': [{'Version': '5.5.0', 'Name': 'Webserver', 'String': 'Webserver (5.5.0)'}, {'Version': '5.5.0', 'Name': 'Tomcat', 'String': 'Tomcat (5.5.0)'}, {'Version': '2.2.0', 'Name': 'Apache', 'String': 'Apache (2.2.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Cartridge', 'Architecture': 'all'},
                    'PHP': {'Status': 'resolved', 'Vendor': '', 'Name': 'PHP', 'Install-Root': '/tmp/vpm/opt/vostok/cartridges', 'Install-Name': 'PHP', 'Quoted-Name': 'PHP', 'Bundles': '', 'Quoted-Version': '5.5.0', 'Package-State': 'Virgin', 'Architecture': 'all', 'Depends': [[{'Predicate': "lambda v: v >= '5'", 'Name': 'Webserver', 'String': 'Webserver (>= 5)'}, {'Predicate': "lambda v: v >= '2.1'", 'Name': 'Apache', 'String': 'Apache (>= 2.1)'}]], 'Version': '5.5.0', 'Role': 'application', 'Build': '1', 'Provides': [{'Version': '5.5.0', 'Name': 'PHP', 'String': 'PHP (5.5.0)'}], 'Conflicts': None, 'DisplayName': '', 'Type': 'Cartridge', 'Description': ''}
                    }

        #self.assertEquals(db, check_db)
                 
if __name__ == '__main__':
    unittest.main()

#
# EOF
