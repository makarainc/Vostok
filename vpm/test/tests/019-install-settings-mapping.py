# ===========================================================================
# Copyright 2009 OSS-1701, Inc.  All Rights Reserved.
#
# This is UNPUBLISHED PROPRIETARY SOURCE CODE of OSS-1701, Inc.  The contents
# of this file may not be disclosed to third parties, copied or duplicated
# in any form, in whole or in part, without the prior written permission of
# OSS-1701, Inc.
# ===========================================================================
#
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/test/tests/019-install-settings-mapping.py $
# $Date: 2010-05-15 21:40:49 +0200 (Sa, 15 Mai 2010) $
# $Revision: 7394 $

import VPM
import unittest

from utils import *

class TestInstallSettingsMapping(unittest.TestCase):

    def setUp(self):
        self.env = VPM.Environment('/tmp/vpm')
        self.p = VPM.Package(self.env)
        self.p.db()

    def tearDown(self):
        rm_rf(self.env.install_root)  

    def testInstall(self):
        s_r = ''
        v = ''
        f = ''
        
        os.mkdir('/tmp/vpm/settings')
        
        data = 'foo > 1.3\tfoo-new\n'
        
        write_file('/tmp/vpm/settings/settings.map',data)
        
        str = self.p._settings_resolve_mapping('/tmp/vpm/settings', '1.4', 'foo')
        self.assertEqual(str, 'foo-new')
        
        str = self.p._settings_resolve_mapping('/tmp/vpm/settings', '1.2', 'foo')
        self.assertEqual(str, 'foo')

if __name__ == '__main__':
    unittest.main()

#
# EOF
