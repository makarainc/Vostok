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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/bash-support/pre-remove.sh $
# $Date: 2010-03-31 02:42:32 +0200 (Mi, 31 Mrz 2010) $
# $Revision: 6415 $

#
# Provides:
#
#   vostok_path     - vostok "root" relative to '/', typically 'opt/vostok'
#
#   remove_path {path}*
#                   - remove as much of each 'path' argument as possible.
#                     'path' arguments must be relative paths and must not
#                     contain symbolic link directory components.

set -e

: ${VS_ROOT:=$(cd -P -- "$(dirname -- "$0")/../.." && pwd -P)}

vostok_path=$(cd -P -- "$VS_ROOT/../.." && pwd -P | sed 's,^/*,,')


function remove_path() {
  for pth in "$@"; do
    case "$pth" in
      /*) 
        echo "Cowardly refusing to remove absolute path: '$pth'." >&2
        return 1
        ;;
      *)                                # reject symlinks to directories
        _p=$(dirname "$pth")

        while test "$_p" != '.'; do
          if test -L "$_p"; then
            echo "Refusing to remove path with embedded symlinks: '$pth'." >&2
            return 1
          fi
          _p=$(dirname "$_p")
        done
        ;;
    esac


    if test -e "$pth"; then
      if test -f "$pth" -o -L "$pth"; then
        /bin/rm -f "$pth"
      elif test -d "$pth"; then
        /bin/rmdir -p --ignore-fail-on-non-empty "$pth"
      else
        echo "Don't know how to remove '$pth'." >&2
        return 1
      fi
    fi

    pth=$(/usr/bin/dirname "$pth")

    while test "$pth" != '.'; do
      if test -e "$pth"; then
        if test -d "$pth"; then
          /bin/rmdir -p --ignore-fail-on-non-empty "$pth"
        else
          echo "Don't know how to remove '$pth'." >&2
          return 1
        fi
      fi
      pth=$(/usr/bin/dirname "$pth")
    done
  done
}

#
# EOF
