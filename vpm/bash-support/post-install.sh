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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/bash-support/post-install.sh $
# $Date: 2010-03-31 02:42:32 +0200 (Mi, 31 Mrz 2010) $
# $Revision: 6415 $

#
# Provides:
#
#   vostok_path     - vostok "root" relative to '/', typically 'opt/vostok'
#   package_path    - package path relative to $vostok_path

set -e

: ${VS_ROOT:=$(cd -P -- "$(dirname -- "$0")/../.." && pwd -P)}

vostok_path=$(cd -P -- "$VS_ROOT/../.." && pwd -P | sed 's,^/*,,')
package_path="packages/$(basename "$VS_ROOT")"

umask 022

#
# EOF
