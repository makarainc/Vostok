#!/usr/bin/env python
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
# $URL: svn+ssh://svn.oss-1701.com/vostok/trunk/vpm/VPM/Lock.py $
# $Date: 2010-03-31 02:42:32 +0200 (Mi, 31 Mrz 2010) $
# $Revision: 6415 $

import fcntl, struct, errno, sys

class LockError (EnvironmentError):
    pass

class Lock (object):
    __MODE_R = 'r'
    __MODE_W = 'w'

    # WARNING: not portable. See definition in /usr/include/bits/fcntl.h
    #
    # Linux 2.6.25 defines
    #
    #     struct flock {
    #         short int l_type;
    #         short int l_whence;
    #     #ifndef __USE_FILE_OFFSET64
    #         __off_t l_start;
    #         __off_t l_len;
    #     #else
    #         __off64_t l_start;
    #         __off64_t l_len;
    #     #endif
    #         __pid_t l_pid;
    #     };
    #
    # The proper format to struct.pack/unpack is thus either 'hhlll' or 'hhqql'
    # if large file support is enabled in the kernel (CONFIG_LBD).
    __FLOCK_LAYOUT = 'hhqql'            # FIXME: find portable solution

    __fd = None

    def _flock_pack(self, cmd):
        return struct.pack(self.__FLOCK_LAYOUT, cmd, 0, 0, 0, 0)

    def _flock_unpack(self, data):
        return struct.unpack(self.__FLOCK_LAYOUT, data)

    def acquire(self, file, mode = 'r'):
        """
        Acquire a read or write lock on a file.  'file' is created (but not
        removed) if it doesn't exist.  'mode' is 'r' or 'w'.
        
        Raises 'LockError' if the lock cannot be acquired, 'ValueError' if
        the 'mode' argument is unsupported, or 'IOError' if 'file' is not
        accessible.  Returns True on success.
        """        
        fd = None
        rv = None
        md = None

        if mode is self.__MODE_R:
            md = fcntl.F_RDLCK
        elif mode is self.__MODE_W:
            md = fcntl.F_WRLCK
        else:
            raise ValueError \
                  ("mode argument '%s' must be one of %s" % \
                   (mode, str((self.__MODE_R, self.__MODE_W))))

        fd = open(file, 'w+')

        try:
            rv = fcntl.fcntl(fd, fcntl.F_SETLK, self._flock_pack(md))
        except IOError, e:
            if e[0] == errno.EAGAIN:
                rv = fcntl.fcntl(fd, fcntl.F_GETLK, self._flock_pack(md))
                fd.close()
                fd = None
                raise LockError, \
                      "Resource currently locked by pid %d" % \
                      self._flock_unpack(rv)[4]
            else:
                fd.close()
                raise

        # success
        self.__fd = fd

        return True 

    def release(self):
        """
        Release the lock held by the object.
        """
        if self.__fd:
            try:
                fcntl.fcntl(self.__fd,
                            fcntl.F_SETLK,
                            self._flock_pack(fcntl.F_UNLCK))
            finally:
                self.__fd.close()
                self.__fd = None


if __name__ == "__main__":
    f = len(sys.argv) > 1 and sys.argv[1] or '/tmp/test.lck'
    m = len(sys.argv) > 2 and sys.argv[2] or 'r'

    def test_lock(f, m):
        l = Lock()
    
        if l.acquire(f, m):
            raw_input('Holding the lock. Hit return to quit. ')
            l.release()

    """
        Process 1               Process 2               Result
        =============================================================
        /tmp/test.lck w
                         	/tmp/test.lck r      => LockError
        (quit)
        -------------------------------------------------------------
        /tmp/test.lck r
                                /tmp/test.lck w      => LockError
        (quit)
        -------------------------------------------------------------
        /tmp/test.lck r
                                /tmp/test.lck r      => OK
        (quit)                  (quit)
        -------------------------------------------------------------
        /tmp/test.lck r
                                /tmp/test2.lck w     => OK
        (quit)                  (quit)
    """
    test_lock(f, m)


#
# EOF
