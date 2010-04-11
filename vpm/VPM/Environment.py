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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/VPM/Environment.py $
# $Date: 2010-03-31 02:42:32 +0200 (Mi, 31 Mrz 2010) $
# $Revision: 6415 $

import logging
import os
import re
import sys

class Environment (object):
    '''
    Global Environment.
    '''
    # User Settings
    debug             = False          # don't trap exceptions (for testing)
    no_hooks          = False          # don't run any hooks (for testing)
    trace_hooks       = False

    # VPM Infrastructure
    lock_dir          = None
    pdb_lock_pathname = None

    lib_dir           = None
    lib_package_dir   = None
    pdb_pathname      = None

    tmp_dir           = None
    tmp_package_dir   = None

    install_root      = None

    package_dir       = None
    cartridge_dir     = None
    application_dir   = None

    # Logging
    log               = None

    # Tracing
    _source_pat       = re.compile('^.*/VPM/')
    _trace_indent     = 0

    def __init__(self, root = '/'):
        self.log = logging.getLogger('vpm')
        logging.basicConfig()
        self.trace_hooks = os.getenv('VPM_TRACE', None)

        self.relocate(root)

    def relocate(self, root):
        '''
        Relocate vpm install root
        @param root: path to package install root
        '''

        if isinstance(root, basestring):
            self.lock_dir          = os.path.join(root, 'var', 'lock', 'vpm')
            self.pdb_lock_pathname = os.path.join(self.lock_dir, 'db.lock')
            self.lib_dir           = os.path.join(root, 'var', 'lib', 'vpm')
            self.lib_package_dir   = os.path.join(self.lib_dir, 'packages')
            self.pdb_pathname      = self.lib_dir
            self.tmp_dir           = os.path.join(root, 'var', 'tmp', 'vpm')
            self.tmp_package_dir   = os.path.join(self.tmp_dir, 'packages')
            self.package_dir       = os.path.join(root,
                                                  'opt', 'vostok', 'packages')
            self.cartridge_dir     = os.path.join(root,
                                                  'opt', 'vostok', 'cartridges')
            #self.application_dir   = os.path.join(root, 'srv', 'applications')
            # FIXME: For Homam the app dir is web-apps
            self.application_dir   = os.path.join(root, 'srv', 'web-apps')
            
            self.install_root      = root
    
    # Tracing
    # ---------------
    # There are two tracing options:
    #
    #   1. if the VPM_TRACE environment variable is set to true, then
    #      cartridge hooks are traced.
    #   2. if trace(True) is called, then vpm functions are traced.

    def _trace(self, frame, event, arg):
        if re.match(self._source_pat, frame.f_code.co_filename):
            if event == 'call':
                print("  " * self._trace_indent,
                      frame.f_code.co_name, frame.f_locals)
                self._trace_indent += 1
            elif event == 'return':
                self._trace_indent -= 1
                print "  " * self._trace_indent, "=> ", arg

        return self._trace
    
    def trace(self, switch = True):
        if switch:
            sys.settrace(self._trace)
        else:
            sys.settrace(None)


#
# EOF
