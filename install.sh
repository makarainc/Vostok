#!/bin/bash
# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/common/build.sh $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

#get current directory
export VS_ROOT="${VS_OSE_ROOT:-$(cd -P -- "$(dirname -- "$0")" && pwd -P)}"

#create installation root directory (allow user to specify prefix)
#TODO: prefix
# create the base layout
install -v -o root -g root -m 0755 -d \
  /opt/vostok/{bin,etc/include,lib/python2.4,sbin,share,usr,var}

echo '*****************Creating log, cache and tmp dirs***********'
mkdir -p /opt/vostok/etc/init.d
mkdir -p /opt/vostok/var/log
mkdir -p /opt/vostok/var/cache
mkdir -p /opt/vostok/var/tmp
mkdir -p /opt/vostok/var/run


mkdir -p /opt/vostok/var/run
mkdir -p /opt/vostok/var/log
mkdir -p /opt/vostok/etc/logrotate.d

#installing vpm
echo 'installing vpm'

support_dir="bash-support"              # install build-*.sh as well for now

install -v -o root -g root -m 0755 -d /opt/vostok/lib/vpm/bash-support

install -v -m 0755 "$VS_ROOT/vpm/bin/vpm" /opt/vostok/bin
install -v -m 0755 "$VS_ROOT/vpm/bin/vostok" /opt/vostok/bin
cp -R "$VS_ROOT/vpm/VPM" /opt/vostok/lib/python2.4
cp -R "$VS_ROOT/vpm/bash-support" /opt/vostok/lib/vpm/bash-support

install -v -m 0755 "$VS_ROOT/util/translators/bin/translator" /opt/vostok/bin
cp -R "$VS_ROOT/util/translators/Translators" /opt/vostok/lib/python2.4

install -v -m 0755 "$VS_ROOT/util/cartridge-support/bin/upstream" /opt/vostok/bin
cp -R "$VS_ROOT/util/cartridge-support/Cartridge" /opt/vostok/lib/python2.4

install -v -o root -g root -m 0644 "$VS_ROOT/ose/altinstall.pth" /usr/lib/python2.4/site-packages/

echo "Set your PYTHONPATH to /opt/vostok/lib/python2.4"
export PYTHONPATH="/usr/lib/python2.4:/opt/vostok/lib/python2.4"

echo "Done"
