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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/bash-support/build-finalize.sh $
# $Date: 2010-03-31 02:42:32 +0200 (Mi, 31 Mrz 2010) $
# $Revision: 6415 $

cat <<_EOF_ >&2
----------------------------------------------------------------------
Build completed in '$build_path'. 

_EOF_

echo -n "Pack now? [Y/n]" >&2
read packp
case "$packp" in
  [nN]*)
    cat <<_EOF_ >&2
Run

  vpm pack '$build_path' /tmp

to create the package.
_EOF_
    ;;
  *)
    cat <<_EOF_ >&2
vpm pack '$build_path' /tmp
_EOF_
    vpm pack "$build_path" /tmp
    ;;
esac

#
# EOF
