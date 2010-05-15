# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/cartridge-support/test/info/configuration/options.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

from Cartridge.Registry import \
    OR, BOOLEAN, INTEGER, STRING, OPTIONS, \
    name, syntax, default, label, help, requires, conflicts, level, tags, memo,\
    NORMAL, ADVANCED, EXPERT, LOCKED

PHONE_NUMBER  = STRING(token = r'\d{3}\.\d{3}\.\d{4}')
FIRST_NAME    = STRING(token = r'\S+')

options = \
[
 {name      : 'Phone',
  syntax    : PHONE_NUMBER,
  default   : '555.123.4567',
  label     : '''A phone number''',
  help      : '''Lorem ipsum.''',
  requires  : (),
  conflicts : (),
  level     : NORMAL,
  tags      : None,
  memo      : None},

 {name      : 'First Name',
  syntax    : FIRST_NAME,
  default   : 'Anonymous',
  label     : '''Your first name.''',
  help      : '''Lorem ipsum.''',
  requires  : (),
  conflicts : (),
  level     : NORMAL,
  tags      : None,
  memo      : None},
]

#
# EOF
