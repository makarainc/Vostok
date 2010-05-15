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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/utils.py $
# $Date: 2010-05-15 21:40:49 +0200 (Sa, 15 Mai 2010) $
# $Revision: 7394 $

import os
import md5
from subprocess import call

import VPM

# TODO
# install simple files in bundle directory
# verify bundle files, e.g. to verify if an upgrade/rollback was successful
# verify control file information, e.g. to verify upgrade/rollback
# package configuration file support, plus verification

class ControlFile (object):
    settings = {}

    def __init__(self):
        self.settings = {'Name'         : None,
             'Version'      : '1.0.0',
             'Provides'     : '',
             'Depends'      : '',
             'Conflicts'    : '',
             'Type'         : 'application',
             'Architecture' : 'all',
             }
    
    def __del__(self):
        self.settings = {}
        
    def write(self, path):
        res = ''
        try:
            for s in self.settings:
                val = self.settings.get(s, '')
                if val != '':
                    res += ("%s:\t%s\n" % (s, val))
        except Exception:
                raise

        write_file(path, res)

class HookScript (object):
    FAIL = True
    SUCCEED = False
    SKIP = None

    hooks = {VPM.PRE_INSTALL_NAME   : SKIP,
             VPM.POST_INSTALL_NAME  : SKIP,
             VPM.CONFIGURE_NAME     : SKIP,
             VPM.DECONFIGURE_NAME   : SKIP,
             VPM.PRE_REMOVE_NAME    : SKIP,
             VPM.POST_REMOVE_NAME   : SKIP,
             VPM.START_NAME         : SKIP,
             VPM.STOP_NAME          : SKIP
             }

    def _create_script_data(self, mode = SKIP):
        #create script data
        #mode 
        exit_code = 0

        if mode is self.SKIP:
            return None

        if mode == self.FAIL:
            exit_code = 1
        elif mode == self.SUCCEED:
            exit_code = 0

        data = ("""#!/bin/bash
        echo "running $0 $@"
        exit %d
        """ % exit_code)

        return data

    def set_mode(self, hook, mode):
        if(hook in self.hooks):
            if mode is self.SKIP or mode is self.SUCCEED or mode is self.FAIL:
                self.hooks[hook] = mode

    def set_modes(self, mode):
        for s in self.hooks.iterkeys():
            if mode is self.SKIP or mode is self.SUCCEED or mode is self.FAIL:
                self.hooks[s] = mode

    def write_scripts(self, p):
        #write script to disk
        for s in self.hooks.iterkeys():
            data = self._create_script_data(self.hooks[s])

            if data is not None:
                file = os.path.join(p, s)
                write_file(file, data)
                os.chmod(file, 0755)

# ---------------
# Helper functions
# ---------------
def create_bundle_data(vpm_name):
    m = md5.new()
    m.update(vpm_name)

    return m.hexdigest()


def make_dirs(dirs):
    for d in dirs.iterkeys():
        os.makedirs(d)
        if dirs[d]:
            owd = os.getcwd()

            os.chdir(d)
            try:
                make_dirs(dirs[d])
            finally:
                os.chdir(owd)

def rm_rf(path):
    cmd = ['/bin/rm', '-rf', path]
    rc = call(cmd)

def write_file(path, data):
    VPM.write_file(path, data)

def read_file(path):
    return VPM.read_file(path)

def make_vpm(name, control_file_data, hook_script_data = None, prefix = '.'):
    dirs = {VPM.BUNDLE_DIR_NAME : None,
            VPM.META_DIR_NAME : {
                                 VPM.HOOK_DIR_NAME : None,
                                 VPM.SETTINGS_DIR_NAME : None
                                 },
            VPM.DATA_DIR_NAME : { 'cache' : None, 'local' : None, 'logs' : None, 'share' : None, 'tmp' : None}
            }

    owd = os.getcwd()

    if prefix != '.':
        os.makedirs(prefix)
    os.chdir(prefix)

    try:
        # rm_rfI(name)
        os.makedirs(name)
        os.chdir(name)

        make_dirs(dirs)

        #create control file 
        control_file_data.write(os.path.join(VPM.META_DIR_NAME, VPM.CONTROL_FILE_NAME))
        
        #create build file
        data = VPM.KEY_BUIL + ': 1'
        write_file(os.path.join(VPM.META_DIR_NAME, VPM.BUILD_FILE_NAME), data)

        #create hook scripts
        if hook_script_data is not None:
            hook_script_data.write_scripts(os.path.join(VPM.META_DIR_NAME, VPM.HOOK_DIR_NAME))

        #write bundle data
        data = create_bundle_data(name)
        write_file(os.path.join(VPM.BUNDLE_DIR_NAME, 'package-file'), data)
    finally:
        os.chdir(owd)


#
# EOF
