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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/bash-support/build-initialize.sh $
# $Date: 2010-03-31 02:42:32 +0200 (Mi, 31 Mrz 2010) $
# $Revision: 6415 $

#
# Input variables (defaults in parentheses):
#
#   build_argc          - nr of arguments (0)
#   build_args          - argument syntax string ("")
#   build_prefix        - prefix portion of build path ("")
#
# Output variables:
#
#   project_path        - absolute, sanitized path to project
#   project_name        - name of project
#   project_version     - version of project
#   project_bundles     - list of bundles as a bash array
#
#   build_path          - full build path (root + prefix + name)
#   build_root          - root portion of build path (the temp directory)
#   build_name          - package directory name portion of build path
#   build_bundle        - package bundle directory

set -E

: ${build_argc:=0}
: ${build_args:=""}
: ${build_prefix:=""}

if test $(id -u) != 0 ; then
  echo "You must be root to run this script. Aborting." >&2
  exit 1
fi

if test $# -ne $build_argc; then
  echo "Usage: $(basename $0) $build_args" >&2
  exit 2
fi

_saved_umask=$(umask)

# _info_dir is not always "info" in the source path but may be "info-dev" or
# somesuch. In the build path, however, it is always "info"
_info_dir=$(basename $(cd -P -- "$(dirname -- "$0")/.." && pwd -P))
test -n "$_info_dir"
project_path=$(cd -P -- "$(dirname -- "$0")/../.." && pwd -P)
test -n "$project_path"

_control_file="$project_path/$_info_dir/control"

project_name=$(sed -n 's/^Name: *//p' "$_control_file")
test -n "$project_name"
project_version=$(sed -n 's/^Version: *//p' "$_control_file")
test -n "$project_version"

build_root="/tmp"
mktemp_stem="/tmp/$project_name"


if [ $# -eq 0 ]; then
  project_bundles=( $(sed -n 's/^Bundles: *//p' "$_control_file" | sed -e 's/,/ /g') )
else
  project_bundles=( "$@" )
fi


__cleanup() {
  case "$build_root" in
    $mktemp_stem*) rm -rf "$build_root" ;;
  esac
  exit 1
}

trap __cleanup ERR INT QUIT TERM

build_root=$(mktemp -d "$mktemp_stem.XXXXXX")
test -n "$build_root"

_prefix="$build_prefix"                 # don't mess with input parameter
if test -n "$_prefix"; then
  _prefix="$_prefix/"
fi

build_name="$project_name-$project_version"
build_path="$build_root/$_prefix$build_name"
build_info="$build_path/info"
build_bundle="$build_path/bundle"

# Public functions to orchestrate the build.  Boilerplate build functions
# that may be called by a package build script.
function svn_to_bundle() {
  if [ -e "$project_path/bundle" ]; then
    echo "Exporting: $project_path/bundle"
    svn --force export "$project_path/bundle" "$build_path/bundle"
  fi
}


function _find_bun() {

  # File exists?  Already found it then.
  if test -f "$1"; then
    echo "$1"
    return 0
  fi

  # Otherwise, check a few likely locations
  for locd in "$project_path" "$build_root" "/var/tmp" "/tmp" "$HOME/bundles"; do
    if [ -f "$locd/$1" ]; then
      echo "$locd/$1"
      return 0
    fi
  done

  # If its a URL, then download it
  if [[ "$bun" =~ '^(http|ftp)://' ]]; then
    dbun=`basename $bun`
    curl --silent -o "/tmp/$dbun" "$bun"
    if [ $? -eq 0 ]; then
      echo "/tmp/$dbun"
      return 0
    fi
  fi

  return 1
}


function unpack_bundles() {
  for _bun in "${project_bundles[@]}" ; do

    bun=`_find_bun $_bun`
    if [ $? -ne 0 ]; then
      echo "Failed to find bundle: $_bun"
      exit 1
    fi

    echo "Unpacking: $bun"
    tar -C "$build_bundle" -zxf "$bun"
    if [ $? -ne 0 ]; then
      echo "Failed to unpack bundle: '$bun'" >&2
      exit 1
    fi
  done
}

function maintainer_config() {
  _cfgpth="${build_path}"/info/configuration
  _cfgcmd="$_cfgpth"/configure.py
  if [ -e "$_cfgcmd" ]; then
    echo "Running configure.py"
    python "$_cfgcmd" 'reset()'
    rm -f "${_cfgpth}"/*.pyc "${_cfgpth}"/*.pyo
  fi
}

function standard_build() {
  svn_to_bundle
  unpack_bundles "$@"
  maintainer_config
}


# install runtime-relevant $_info_dir files from well-known locations. Do
# this halfway safely by controlling ownership and permissions. As a result,
# anything that shouldn't be root:root and 755 or 644, respectively, must be
# fixed up within $_info_dir/build/build. The only exception to this rule
# are hooks, which are automatically made executable.

pushd "$project_path/$_info_dir" > /dev/null

function _install_file() {
  if test -e "$1" || test -n "$2"; then
    install -p -m 0644 -o root -g root "$1" "$build_path/info/$1"
  fi
}
function _install_symlink() {
  if test -e "$1" || test -n "$2"; then
    v=$(readlink "$1")

    case "$v" in
      /*)
        echo "Cannot install symlinks to absolute locations." >&2
        return 1
        ;;
      ../*|*/../*)
        echo "Warning: installing symlink containing '..'." >&2
        ;;
    esac

    cp -d "$1" "$build_path/info/$1"
  fi    
}
function _install_dir() {
  if test -e "$1" || test -n "$2"; then
    install -p -m 0755 -o root -g root -d "$build_path/info/$1"
  fi
}
function _install_tree() {
  if test -e "$1"; then
    _install_dir "$1"
    for item in $(ls -A1 "$1"); do
      case "$item" in
        .svn|*~|*.pyc)                  # also blacklist pyc files
          ;;
        *)
          path="$1/$item"
          if test -d "$path"; then
            _install_tree "$path"
          elif test -L "$path"; then
            _install_symlink "$path"
          elif test -f "$path"; then
            _install_file "$path"
          fi
          ;;
      esac
    done
  fi
}

_install_dir  '.'               require

_install_file 'control'         require
_install_file 'changelog'
_install_file 'deployment-descriptor.xml'
_install_file 'files'

_install_tree 'alternatives'
_install_tree 'hooks'
_install_tree 'setup'
_install_tree 'configuration'
_install_tree 'defaults'

if test -d "$build_path/info/hooks"; then
  # exlude files matching *.* (hooks should not have dots, but auxiliary
  # files such as "common.sh" or "foo.py" will. FIXME document)
  for f in $(ls -A1 "$build_path/info/hooks" | grep -v '[.]'); do
    chmod 755 "$build_path/info/hooks/$f"
  done
fi

popd > /dev/null

unset _prefix
unset _saved_umask
unset _control_file
unset _info_dir

unset _install_file
unset _install_symlink
unset _install_dir
unset _install_tree

#
# EOF
