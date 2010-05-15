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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/VPM/Utils.py $
# $Date: 2010-04-17 12:57:37 +0200 (Sa, 17 Apr 2010) $
# $Revision: 6745 $

import os
import os.path
import cPickle

def read_file(pathname, error = False):
    data = None

    if not os.path.exists(pathname):
        if error:
            raise ValueError("'%s': not found" % pathname)
    elif not os.path.isfile(pathname):
        if error:
            raise ValueError("'%s': not a file" % pathname)
    else:
        f = open(pathname, 'rU')

        try:
            data = f.read()
        finally:
            f.close()

    return data

def write_file(pathname, data):
    fd = open(pathname, 'w')

    try:
        fd.write(data)
    finally:
        fd.close()

def serialize(pathname, data):
    fd = open(pathname, 'w')
    
    try:
        cPickle.dump(data, fd, 2) # use protocol 2
    finally:
        fd.close()
        
def unserialize(pathname):
    fd = open(pathname, 'rb')
    data = None
    
    try:
        data = cPickle.load(fd)
    finally:
        fd.close()
        
    return data
#
# EOF
