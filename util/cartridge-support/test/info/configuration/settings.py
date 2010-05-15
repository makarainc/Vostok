# ===========================================================================
# Copyright 2010 Makara, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of Makara, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# Makara, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/util/cartridge-support/test/info/configuration/settings.py $
# $Date: 2010-03-13 17:32:55 +0100 (Sa, 13 Mrz 2010) $
# $Revision: 6047 $

from Cartridge.Registry import item, group, scope

settings = [group(('Freedom Fighters'),
              item('First Name', 'Klumpkauski'),
              item('Last Name',  'Brschtschevich'),
              item('Phone',      '650.887.1239'))]

#
# EOF
