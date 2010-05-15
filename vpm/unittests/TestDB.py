'''
Created on 15.03.2010

@author: cmk
'''
import unittest

import VPM
from utils import *
from VPM.Constants import DB_KEY_ROLE, DB_KEY_NAME

class TestDBApi(unittest.TestCase):

    test1 = 'Webserver'
    test2 = 'PHP'
    test3 = 'JAVA'
    test4 = 'App'
    
    env = None
    p = None
    db = None

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

        _, self.v1, _ = self.p.pack(self.test1, '.')
        self.vpmfile1 = self.v1

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = self.test2
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'
        ctrl_d2.settings['Depends'] = 'Webserver (>= 5) | Apache (>= 2.1)'

        make_vpm(self.test2, ctrl_d2, hooks)

        _, self.v2, _ = self.p.pack(self.test2, '.')
        self.vpmfile2 = self.v2

        # grandchild vpm
        ctrl_d3 = ControlFile()
        ctrl_d3.settings['Name'] = self.test3
        ctrl_d3.settings['Type'] = 'Cartridge'
        ctrl_d3.settings['Provides'] = 'JAVA'
        ctrl_d3.settings['Depends'] = 'Tomcat (>= 5.0) | Tomcat (<=6.0)'

        make_vpm(self.test3, ctrl_d3, hooks)

        _, self.v3, _ = self.p.pack(self.test3, '.')
        self.vpmfile3 = self.v3
        
        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = self.test4
        ctrl_d4.settings['Type'] = 'Application'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'Apache (>= 2.1), PHP'

        make_vpm(self.test4, ctrl_d4, hooks)

        _, self.v4, _ = self.p.pack(self.test4, '.')
        self.vpmfile4 = self.v4
        
        #install apache
        self.p.install(self.vpmfile1)
        
        #install php
        self.p.install(self.vpmfile2)

        # install java
        self.p.install(self.vpmfile3)        
        
        #install app
        self.p.install(self.vpmfile4)

    def tearDown(self):
        rm_rf(self.vpmfile1)
        rm_rf(self.test1)

        rm_rf(self.vpmfile2)
        rm_rf(self.test2)

        rm_rf(self.vpmfile3)
        rm_rf(self.test3)
        
        rm_rf(self.vpmfile4)
        rm_rf(self.test4)

        rm_rf(self.env.install_root)
    
    def test_lock_read(self):
        res = self.p.db().lock('r')
        self.assertEquals(res, True)
        
        self.p.db().unlock()
        
    def test_lock_write(self):
        res = self.p.db().lock('w')
        self.assertEquals(res, True)
        
        self.p.db().unlock()

    def test_check_install(self):        
        _, info, _ = self.p.info('App', 1)
        res, _ = self.p.db().check_install(info)
        
        self.assertTrue(res)

    def test_check_remove(self):        
        res, _ = self.p.db().check_remove('App')
        
        self.assertTrue(res)

    def test_list_packages(self):
        res = self.p.db().list_packages()
        
        test = [{'Status': 'resolved', 'Version': '1.0.0', 'Name': 'App', 'Build': '1'}, {'Status': 'resolved', 'Version': '1.0.0', 'Name': 'JAVA', 'Build': '1'}, {'Status': 'resolved', 'Version': '1.0.0', 'Name': 'PHP', 'Build': '1'}, {'Status': 'resolved', 'Version': '5.5.0', 'Name': 'Webserver', 'Build': '1'}]
        
        self.assertEqual(res, test)

#    FIXME: Test returns empty list, should list packages
#    def test_filter_packages(self):        
#        res = self.p.db().filter_packages('Name', 'PHP')
#        
#        test = []
        
    def test_status(self):
        res = self.p.db().status('App')
        
        self.assertEqual(VPM.DB.RESOLVED, res)

    def test_lookup(self):
        res = self.p.db().lookup('App')
        
        test = 'App'
        self.assertEqual(res.Name, test)

    def test_resolve(self):
        res = self.p.db().resolve('Apache')
        
        test = self.p.db().lookup('Webserver')
        
        self.assertEquals(res, test.Name)

    def test_resolve_dependency_chain(self):
        res = self.p.db().resolve_dependency_chain('App')
        
        test = ['PHP', 'Webserver']
        
        self.assertEqual(res, test)

    def test_lookup_dependency_chain(self):
        res = self.p.db().lookup_dependency_chain('App')
        
        test1 = self.p.db().lookup('PHP')
        test2 = self.p.db().lookup('Webserver')
        
        self.assertEquals(res[0].toString(), test1.toString())
        self.assertEquals(res[1].toString(), test2.toString())

    def test_update_dependency_table(self):
        dtentry = VPM.DependencyTableInfo()
        pr = VPM.ProvidesInfo('Apache', '2.2', '')                      
        pr._SelectedFeature = 'Webserver'
                        
        dtentry.setProvider(pr)

        # update dt
        ft = VPM.DependsInfo('Apache', '2.2', 'Apache (2.1)')
        dtentry.addFeature(ft)
        
        self.p.db().update_dependency_table('App2', dtentry)
        
        test = self.p.db().get_dependency_table_info('App2')
        
        # hack to verify equality
        self.assertEquals(test[0].Provider.Name, dtentry.Provider.Name)

    def test_remove_dependency_table_info(self):
        self.p.db().remove_dependency_table_info('App')
        
        test = self.p.db().get_dependency_table_info('App')
        
        self.assertEquals(None, test)

    def test_find_depending_packages(self):
        res = self.p.db().find_depending_packages('Webserver')
        
        test = ['App', 'PHP', 'JAVA']
        
        self.assertEqual(res, test)

    def test_find_feature_packages(self):
        res = self.p.db().find_feature_packages('PHP', 'App')
        
        test = VPM.ProvidesInfo('PHP','1.0.0','')
        self.assertEqual(res.Name, test.Name)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()