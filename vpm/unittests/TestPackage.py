'''
Created on 21.04.2010

@author: cmk
'''
import unittest

import VPM
from utils import *
import zipfile

class TestPackage(unittest.TestCase):

    env = None
    p = None
    
    testroot = '/tmp/vpm/'
    
    testbuild = '/tmp/vpm_build/build'
    testpackages = '/tmp/vpm_build/packages'
    testscratch = '/tmp/vpm_build/scratch'
    
    def make_default_package(self):                
        ctrl = ControlFile()
        ctrl.settings['Name'] = 'foo'
        ctrl.settings['Version'] = '2.0.0'
        ctrl.settings['Type'] = 'Cartridge'
        ctrl.settings['Provides'] = 'foobar (3.0.0)'
        ctrl.settings['Bundles'] = 'foobar'
        
        return ctrl
    
    def setUp(self):        
        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)
        
        #os.makedirs(self.testbuild, 0755)
        os.makedirs(self.testpackages, 0755)
        os.makedirs(self.testscratch, 0755)
        
        self.p.db() # init testroot dirs
    
    def tearDown(self):        
        rm_rf(self.testbuild)
        rm_rf(self.testpackages)
        rm_rf(self.testscratch)
        
        rm_rf(self.testroot)

    def test_pack(self):
        #    def pack(self, build_root, dest_dir):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        res, val, err = self.p.pack(self.testbuild, self.testpackages)
        
        self.assertEqual(res, True)
        self.assertEqual(val, 'foo_2.0.0-1_all.vpm')
        self.assertEqual(err, None)
        
        self.assertEqual(self.p._validate_package(os.path.join(self.testpackages,val)), True)
        
    def test_unpack(self):
        #    def unpack(self, package, dest_dir):        
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        _, n, _ = self.p.pack(self.testbuild, self.testpackages)
        
        package = os.path.join(self.testpackages, n)
        res, _, err = self.p.unpack(package, self.testscratch)
        
        self.assertEqual(res, True)
        self.assertEqual(err, None)

    def test_package_name(self):
        #    def package_name(self, control_file, build_file = None):
        package_name = 'foo_2.0.0-1_all.vpm'
        
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)
        
        cf = os.path.join(self.testbuild, VPM.META_DIR_NAME, VPM.CONTROL_FILE_NAME)
        bf = os.path.join(self.testbuild, VPM.META_DIR_NAME, VPM.BUILD_FILE_NAME)
        
        _, val, _ = self.p.package_name(cf, bf)
        
        self.assertEqual(val, package_name)

    def test_install(self):
        #    def install(self, package, dest_root = None, deploy_mode = None):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        res, _, _ = self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        self.assertEqual(res, True)
        
        _, val, _ = self.p.info('foo')
        self.assertEqual('foo', val['Name'])

    def test_remove(self):
        #    def remove(self, name, deploy_mode = None):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        res, _, _ = self.p.remove('foo', VPM.DEPLOY_MODE_MANUAL)
        self.assertTrue(res)
        
        _, val, _ = self.p.info('foo')
        self.assertEqual(None, val)

    def test_purge(self):
        #    def remove(self, name, deploy_mode = None):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        res, _, _ = self.p.purge('foo', VPM.DEPLOY_MODE_MANUAL)
        self.assertTrue(res)
        
        _, val, _ = self.p.info('foo')
        self.assertEqual(None, val)

    def test_installable(self):
        #    def installable(self, package):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        res, val, _ = self.p.installable(os.path.join(self.testpackages,v))
        self.assertTrue(res)
        self.assertTrue(val)        

    def test_removable(self):
        #    def removable(self, name):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        res, val, _ = self.p.removable('foo')
        self.assertTrue(res)
        self.assertTrue(val)

    def test_info(self):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        res, val, _ = self.p.info('foo',1)
        self.assertTrue(res)
        self.assertEquals(val.Name, 'foo')
        
        res, val, _ = self.p.info('foo')
        self.assertTrue(res)
        self.assertEquals(val['Name'], 'foo')
        
    def test_list_available(self):
        #    def list_available(self, roles = [], repositories = []):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        avail = self.p.list_available([], [])
        
        test = {'Status': 'resolved', 'Version': '2.0.0', 'Role': None, 'Name': 'foo', 'Build': '1'}
        self.assertEquals(len(avail['local']),1)
        self.assertEqual(avail['local'][0], test)

    def test_start(self):
        #    def start(self, package, app_env=None):
        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = 'PHP'
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'

        make_vpm(self.testbuild + '/PHP', ctrl_d2, hooks)

        _, v2, _ = self.p.pack(self.testbuild + '/PHP', '.')

        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = 'App'
        ctrl_d4.settings['Type'] = 'Application'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'PHP'

        make_vpm(self.testbuild  + '/App', ctrl_d4, hooks)

        _, v4, _ = self.p.pack(self.testbuild  + '/App', '.')

        #install php
        self.p.install(v2)

        #install app
        self.p.install(v4)
        
        res, _, _ = self.p.start('App')
        #Stupid test, make sure everything in the start process works, except
        #for the start hook itself
        self.assertTrue(res)

    def test_stop(self):
        #    def stop(self, package, app_env=None):
        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = 'PHP'
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'

        make_vpm(self.testbuild + '/PHP', ctrl_d2, hooks)

        _, v2, _ = self.p.pack(self.testbuild + '/PHP', '.')

        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = 'App'
        ctrl_d4.settings['Type'] = 'Application'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'PHP'

        make_vpm(self.testbuild  + '/App', ctrl_d4, hooks)

        _, v4, _ = self.p.pack(self.testbuild  + '/App', '.')

        #install php
        self.p.install(v2)

        #install app
        self.p.install(v4)
        
        self.p.start('App') # Need to start the app first
        
        res, _, _ = self.p.stop('App')

        #Stupid test, make sure everything in the stop process works, except
        #for the stop hook itself
        self.assertTrue(res)

    def test_restart(self):
        #    def restart(self, package):
        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = 'PHP'
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'

        make_vpm(self.testbuild + '/PHP', ctrl_d2, hooks)

        _, v2, _ = self.p.pack(self.testbuild + '/PHP', '.')

        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = 'App'
        ctrl_d4.settings['Type'] = 'Application'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'PHP'

        make_vpm(self.testbuild  + '/App', ctrl_d4, hooks)

        _, v4, _ = self.p.pack(self.testbuild  + '/App', '.')

        #install php
        self.p.install(v2)

        #install app
        self.p.install(v4)
        
        self.p.start('App') # Need to start the app first

        # TODO: check if this is correct
        res, _, _ = self.p.restart('App')

        #Stupid test, make sure everything in the stop process works, except
        #for the stop hook itself
        self.assertTrue(res)

    def test_get_control_info(self):
        #    def get_control_info(self, path):        
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)
        
        cf = os.path.join(self.testbuild, VPM.META_DIR_NAME, VPM.CONTROL_FILE_NAME)
        
        _, val, _ = self.p.get_control_info(cf)
        
        self.assertEquals(ctrl.settings['Name'], val.Name)

    def test_get_build_info(self):
        #    def get_build_info(self, path):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)
        
        bf = os.path.join(self.testbuild, VPM.META_DIR_NAME, VPM.BUILD_FILE_NAME)
        
        _, val, _ = self.p.get_build_info(bf)
        
        test = {VPM.KEY_BUIL :'1'}
        self.assertEquals(test, val)

    def test_set_control_info(self):
        cpath = os.path.join(self.testbuild,'info/control')
        if not os.path.exists(os.path.join(self.testbuild, VPM.META_DIR_NAME)):
            os.makedirs(os.path.join(self.testbuild, VPM.META_DIR_NAME), 0755)
            
        cdata = """Name: App
Version: 1.0.0
Architecture: all
Provides: App
Depends: JAVA
Type: Application"""

        cinfo = VPM.ControlInfo(cdata, '<none>')        
        
        res, _, _ = self.p.set_control_info(cinfo, cpath)
        self.assertTrue(res)
        
        test = read_file(cpath)
        self.assertEquals(test, cinfo.toString())

    def test_set_build_info(self):
        bpath = os.path.join(self.testbuild,'info/changelog')
        if not os.path.exists(os.path.join(self.testbuild, VPM.META_DIR_NAME)):
            os.makedirs(os.path.join(self.testbuild, VPM.META_DIR_NAME), 0755)
            
        #    def set_build_info(self, binfo, path):
        binfo = {'Build' : 1}
        
        self.p.set_build_info(binfo, bpath)
        
        test = read_file(bpath)
        self.assertEquals(test, 'Build: 1\n')

    def test_get_scaffolding(self):
        # preparation
        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = 'PHP'
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'

        make_vpm(self.testbuild + '/PHP', ctrl_d2, hooks)

        _, v2, _ = self.p.pack(self.testbuild + '/PHP', '.')

        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = 'App'
        ctrl_d4.settings['Type'] = 'Application'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'PHP'

        make_vpm(self.testbuild  + '/App', ctrl_d4, hooks)

        _, v4, _ = self.p.pack(self.testbuild  + '/App', '.')

        #install php
        self.p.install(v2)

        #install app
        self.p.install(v4)

        #    def get_scaffolding(self, provider = None, dependency = None, dependant = None):
        _, info, _ = self.p.info('App',1)

        deps = info.Depends
        dep = deps[0]

        _, val, _ = self.p.get_scaffolding(None, dep, 'App')
        
        _, test, _ = self.p.info('PHP',1)
        self.assertEqual(val[0].toString(), test.toString())

    def test_get_setup_directory(self):
        #    def get_setup_directory(self, package_name, dependency, shared):
        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)

        # child vpm
        ctrl_d2 = ControlFile()
        ctrl_d2.settings['Name'] = 'PHP'
        ctrl_d2.settings['Type'] = 'Cartridge'
        ctrl_d2.settings['Provides'] = 'PHP'

        make_vpm(self.testbuild + '/PHP', ctrl_d2, hooks)

        _, v2, _ = self.p.pack(self.testbuild + '/PHP', '.')

        # app vpm
        ctrl_d4 = ControlFile()
        ctrl_d4.settings['Name'] = 'App'
        ctrl_d4.settings['Type'] = 'Application'
        ctrl_d4.settings['Provides'] = 'App'
        ctrl_d4.settings['Depends'] = 'PHP'

        make_vpm(self.testbuild  + '/App', ctrl_d4, hooks)

        _, v4, _ = self.p.pack(self.testbuild  + '/App', '.')

        #install php
        self.p.install(v2)

        #install app
        self.p.install(v4)

        _, val, _ = self.p.get_setup_directory('App', 'PHP', True)

        self.assertEquals(val, ['/tmp/vpm/srv/web-apps/App/App/info/setup/PHP', False])

    def test_get_cartridge_install_dir(self):
        #    def get_cartridge_install_dir(self, cartridge_name):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        res = self.p.get_cartridge_install_dir('foo')
        
        test = '/tmp/vpm/opt/vostok/cartridges/foo'
        self.assertEqual(res, test)
        
# Needs a real package with configuration subsystem
#    def test_get_cartridge_configuration_module(self):
#        #    def get_cartridge_configuration_module(self, cartridge_name):
#        pass

    def test_get_hook(self):
        #    def get_hook(self, package, hook):
        
        hooks = HookScript()
        hooks.set_modes(HookScript.SUCCEED)
        
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl, hooks)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        _, val, _ = self.p.get_hook('foo', 'start')
        
        test = '/tmp/vpm/opt/vostok/cartridges/foo/info/hooks/start'
        self.assertEqual(val, test)

    def test_get_bundle_dir(self):
        #    def get_bundle_dir(self, package):
        ctrl = self.make_default_package()

        make_vpm(self.testbuild, ctrl)

        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)

        _, v, _ = self.p.pack(self.testbuild, self.testpackages)
        
        self.p.install(os.path.join(self.testpackages,v), None, VPM.DEPLOY_MODE_MANUAL)
        
        _, val, _ = self.p.get_bundle_dir('foo')
        
        test = '/tmp/vpm/opt/vostok/cartridges/foo/bundle'
        self.assertEqual(val, test)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()