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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/VPM/Constants.py $
# $Date: 2010-05-15 21:40:49 +0200 (Sa, 15 Mai 2010) $
# $Revision: 7394 $

import os

BUNDLE_DIR_NAME     = 'bundle'
META_DIR_NAME       = 'info'
DATA_DIR_NAME       = 'data'
DOT_DATA_DIR_NAME   = '.data'
DATA_DIRS           = frozenset(['cache','local','logs','share','tmp'])

CONTROL_FILE_NAME   = 'control'
BUILD_FILE_NAME     = 'changelog'
LOCATION_FILE_NAME  = 'location'        # env.lib_dir/package/PKG.location only
VPM_LOCK_FILE_NAME  = '.vpm.lock'       # package-specific lock file
CHECKSUM_FILE_NAME  = 'md5sums'         # FIXME move to sha256?
#FILELIST_FILE_NAME  = 'list'
FILEMODE_FILE_NAME  = 'files'
SETTINGS_MAP_NAME   = 'settings.map'
SIGNATURE_FILE_NAME = 'signature'
VERSION_FILE_NAME   = 'version'

ZIP_EXCLUDE = ['.svn', 'CVS', VPM_LOCK_FILE_NAME]

# VPM Hooks
HOOK_DIR_NAME       = 'hooks'
PRE_INSTALL_NAME    = 'pre-install'      # FIXME reserved?
POST_INSTALL_NAME   = 'post-install'
CONFIGURE_NAME      = 'configure'
DECONFIGURE_NAME    = 'deconfigure'
PRE_REMOVE_NAME     = 'pre-remove'
POST_REMOVE_NAME    = 'post-remove'      # FIXME reserved?
INFO_NAME           = 'info'
START_NAME          = 'start'
STOP_NAME           = 'stop'
# RESTART_NAME       = 'restart'        # FIXME used?
RELOAD_NAME         = 'reload'
HOOK_ADJ_PRIORITY   = 2

# Scaffolding
DEFAULTS_DIR_NAME   = 'defaults'
IDL_FILE_NAME       = 'idl.py'
SHARED_COPY_LINK_NAME = 'development'

# Settings
SETTINGS_DIR_NAME  = 'setup'
SETTINGS_FILE_NAME = 'settings.py'      # FIXME still used?

# Configuration                         # FIXME obsolete or internal use only
CFG_DIR_NAME       = 'configuration'
CFG_BASENAME       = 'configure'
CFG_FILE_NAME      = os.path.join(CFG_DIR_NAME, CFG_BASENAME + '.py')

# Build
KEY_BUIL = 'Build'
VAL_BUIL_DEFAULT = '1'

KEY_INSR = 'Install-Root'
KEY_INSN = 'Install-Name'

# PackageDatabase Constants
DB_KEY_NAME = 'Name'
DB_KEY_VERS = 'Version'
DB_KEY_BUIL = 'Build'
DB_KEY_STAT = 'Status'
DB_KEY_DEPS = 'Depends'
DB_KEY_CONF = 'Conflicts'
DB_KEY_ROLE = 'Role'

# Package States
PSTATE_VIRGIN     = 'Virgin'
PSTATE_SNAP       = 'Snapshot'
    
# Type Constants
VAL_TYPE_CRT      = 'Cartridge'
VAL_TYPE_PKG      = 'Package'
VAL_TYPE_APP      = 'Application'
    
# Role Constants
# Roles are used for application "stack" selection in the UI
VAL_ROLE_STA      = 'www-static'
VAL_ROLE_STA_E    = 'www-static:extension'
VAL_ROLE_DYN      = 'www-dynamic'
VAL_ROLE_DYN_E    = 'www-dynamic:extension'
VAL_ROLE_RTM      = 'runtime'
VAL_ROLE_RTM_E    = 'runtime:extension'
VAL_ROLE_APP      = 'application'
VAL_ROLE_DBM      = 'database'
VAL_ROLE_DBM_E    = 'database:extension'
               
##
VPM_VERSION            = '2.0'
VPM_VERSIONS_SUPPORTED = frozenset([VPM_VERSION])
VPM_PKG_EXTENSION      = 'vpm'

BIN_RM    = '/bin/rm'
BIN_TAR   = '/bin/tar'
BIN_UNZIP = '/usr/bin/unzip'
BIN_ZIP   = '/usr/bin/zip'
BIN_GREP  = '/bin/grep'
BIN_FIND  = '/usr/bin/find'

DEPLOY_MODE_MANUAL = 'manual'

VS_ACTION_INSTALL  = 'install'
VS_ACTION_REMOVE   = 'remove'


#
# EOF
