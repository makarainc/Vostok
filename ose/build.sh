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
echo '*****************Preparing build **************'

export VS_OSE_ROOT="${VS_OSE_ROOT:-$(cd -P -- "$(dirname -- "$0")/.." && pwd -P)}"
export VS_OSE_BASE=$VS_OSE_ROOT/ose

echo $VS_OSE_ROOT
echo $VS_OSE_BASE

rm -rf $VS_OSE_BASE/build
mkdir -p $VS_OSE_BASE/build/vostok
mkdir -p $VS_OSE_BASE/build/vostok/util
mkdir -p $VS_OSE_BASE/build/vostok/ose

#package build from build dir
cd $VS_OSE_BASE/build

cp -R $VS_OSE_ROOT/vpm $VS_OSE_BASE/build/vostok
cp -R $VS_OSE_ROOT/util/translators $VS_OSE_BASE/build/vostok/util
cp -R $VS_OSE_ROOT/util/cartridge-support $VS_OSE_BASE/build/vostok/util
cp -R $VS_OSE_ROOT/ose/altinstall.pth $VS_OSE_BASE/build/vostok/ose

cp $VS_OSE_BASE/install.sh $VS_OSE_BASE/build/vostok
cp $VS_OSE_BASE/INSTALL $VS_OSE_BASE/build/vostok
cp $VS_OSE_BASE/README $VS_OSE_BASE/build/vostok

tar czf vostok.tar.gz vostok
