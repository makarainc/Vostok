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
# $Date: 2010-04-10 00:29:29 +0200 (Sa, 10 Apr 2010) $
# $Revision: 6599 $

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

# Dependency Table Keys
KEY_DT_FT           = 'feature'
KEY_DT_PROV         = 'provider'
KEY_DT_PROV_SF      = 'sel-feature' # selected feature
KEY_DT_VIRT         = 'virtual'

#
# Control & Build File Fields
# ---------------------------

# Core information
KEY_NAME           = 'Name'             # this is the only required field

KEY_VERS           = 'Version'
VAL_VERS_DEFAULT   = '0.0.0'

KEY_BUIL           = 'Build'
VAL_BUIL_DEFAULT   = '1'                # start build numbers at '1'
BUILD_FORMAT       = "%s: %s\n"         # FIXME encapsulate in write_build_file

KEY_ARCH           = 'Architecture'
VAL_ARCH_DEFAULT   = 'all'              # assume non-binary format
VALS_ARCH          = frozenset(['i686', 'amd64', 'all'])

# Provides, Depends, Conflicts are used for dependency declarations
KEY_PROV           = 'Provides'
VAL_PROV_DEFAULT   = ''
                   
KEY_DEPS           = 'Depends'
VAL_DEPS_DEFAULT   = ''
                   
KEY_CONF           = 'Conflicts'
VAL_CONF_DEFAULT   = ''

# Additional informational fields
KEY_DESC           = 'Description'      # text
VAL_DESC_DEFAULT   = ''

KEY_VEND           = 'Vendor'           # e.g. IBM vs Sun JRE
VAL_VEND_DEFAULT   = ''

KEY_TITL           = 'DisplayName'      # if that needs to be different
VAL_TITL_DEFAULT   = ''

KEY_DLGT           = 'Delegate'
VAL_DLGT_DEFAULT   = ''                 # Empty by default. 
                                        # Must be set explicitly

KEY_BNDL           = 'Bundles'          # List of bundles, used at build time.
VAL_BNDL_DEFAULT   = ''


# Type is used internally (vpm's are treated differently based on type)
KEY_TYPE           = 'Type'
VAL_TYPE_CRT       = 'Cartridge'
VAL_TYPE_PKG       = 'Package'
VAL_TYPE_APP       = 'Application'
VAL_TYPE_DEFAULT   = VAL_TYPE_APP       # optional for applications
VALS_TYPE          = frozenset([VAL_TYPE_CRT, VAL_TYPE_PKG, VAL_TYPE_APP])
                   
# Roles are used for application "stack" selection in the UI
KEY_ROLE           = 'Role'
VAL_ROLE_STA       = 'www-static'
VAL_ROLE_STA_E     = 'www-static:extension'
VAL_ROLE_DYN       = 'www-dynamic'
VAL_ROLE_DYN_E     = 'www-dynamic:extension'
VAL_ROLE_RTM       = 'runtime'
VAL_ROLE_RTM_E     = 'runtime:extension'
VAL_ROLE_APP       = 'application'
VAL_ROLE_DBM       = 'database'
VAL_ROLE_DBM_E     = 'database:extension'
VAL_ROLE_DEFAULT   = VAL_ROLE_APP       # optional for applications
VALS_ROLE          = frozenset([VAL_ROLE_STA, VAL_ROLE_STA_E, VAL_ROLE_DYN, 
                                VAL_ROLE_DYN_E, VAL_ROLE_RTM, VAL_ROLE_RTM_E, 
                                VAL_ROLE_APP, VAL_ROLE_DBM, VAL_ROLE_DBM_E])

#KEY_TAG = 'Tags'
#VAL_TAG = ''
#VAL_TAG_RUN = 'runnable'
#VAL_TAG_END = 'endpoint'
#VAL_TAG_DEFAULT = frozenset([])
  
# Parsed Control File Keys
KEY_NQUO      = 'Quoted-Name'
KEY_VQUO      = 'Quoted-Version'
KEY_PRED      = 'Predicate'
KEY_STR       = 'String'
KEY_STAT      = 'Status'

VAL_STAT_DEFAULT = 'imported' # hack

KEY_INSR          = 'Install-Root'
VAL_INSR_DEFAULT  = ''

KEY_INSN          = 'Install-Name'
VAL_INSN_DEFAULT  = ''

KEY_INSR          = 'Install-Root'
VAL_INSR_DEFAULT  = ''

KEY_INSN          = 'Install-Name'
VAL_INSN_DEFAULT  = ''

KEY_PSTATE    = 'Package-State'
PSTATE_VIRGIN = 'Virgin'
PSTATE_SNAP   = 'Snapshot'
VAL_PSTATE_DEFAULT = PSTATE_VIRGIN

# We keep these as ordered lists representing canonical ordering on write-out
CKEYS_REQ = [KEY_NAME]
CKEYS_OPT = [KEY_VERS, KEY_ARCH,              # core information
             KEY_PROV, KEY_DEPS, KEY_CONF,    # dependencies
             KEY_DESC, KEY_VEND, KEY_TITL,    # addt'l information
             KEY_DLGT,                        # delegate pkg control
             KEY_TYPE, KEY_ROLE,              # classification
             KEY_BNDL,
             KEY_INSR, KEY_INSN,
             KEY_STAT, KEY_PSTATE]             # Fields required for scaffolding

CKEYS_QUO = [KEY_NQUO, KEY_VQUO]

BKEYS_REQ = [KEY_BUIL]
BKEYS_OPT = []
BKEYS_QUO = []

LKEYS_REQ = [KEY_INSR, KEY_INSN]
LKEYS_OPT = []
LKEYS_QUO = []

CINFO_DEFAULT = {KEY_VERS : VAL_VERS_DEFAULT,
                 KEY_BUIL : VAL_BUIL_DEFAULT,
                 KEY_ARCH : VAL_ARCH_DEFAULT,
                 KEY_PROV : VAL_PROV_DEFAULT,
                 KEY_DEPS : VAL_DEPS_DEFAULT,
                 KEY_CONF : VAL_CONF_DEFAULT,
                 KEY_DESC : VAL_DESC_DEFAULT,
                 KEY_VEND : VAL_VEND_DEFAULT,
                 KEY_TITL : VAL_TITL_DEFAULT,
                 KEY_DLGT : VAL_DLGT_DEFAULT,
                 KEY_TYPE : VAL_TYPE_DEFAULT,
                 KEY_ROLE : VAL_ROLE_DEFAULT,
                 KEY_BNDL : VAL_BNDL_DEFAULT,
                 KEY_INSR : VAL_INSR_DEFAULT,
                 KEY_INSN : VAL_INSN_DEFAULT,
                 KEY_STAT : VAL_STAT_DEFAULT,
                 KEY_PSTATE: VAL_PSTATE_DEFAULT
                 }

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
