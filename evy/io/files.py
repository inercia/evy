#
# Evy - a concurrent networking library for Python
#
# Unless otherwise noted, the files in Evy are under the following MIT license:
#
# Copyright (c) 2012, Alvaro Saurin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#
import sys
import array

import socket
from socket import socket as _original_socket


from evy.support import get_errno

from evy.hubs import trampoline, wait_read, wait_write
from evy.hubs import get_hub

from evy.uv.interface import libuv, ffi, handle_is_active, cast_to_handle

import errno
import os


# Emulate _fileobject class in 3.x implementation
# Eventually this internal socket structure could be replaced with makefile calls.
try:
    _fileobject = socket._fileobject
except AttributeError:
    def _fileobject (sock, *args, **kwargs):
        return _original_socket.makefile(sock, *args, **kwargs)



__all__ = []




class _UvSocketDuckForFd(object):
    """
    Class implementing all socket method used by _fileobject in cooperative manner
    using low level os I/O calls.
    """

    def __init__ (self, fileno):
        self._fileno = fileno

    @property
    def _sock (self):
        return self

    def fileno (self):
        return self._fileno

    def recv (self, buflen):
        while True:
            try:
                data = os.read(self._fileno, buflen)
                return data
            except OSError, e:
                if get_errno(e) != errno.EAGAIN:
                    raise IOError(*e.args)
            wait_read(self)

    def sendall (self, data):
        len_data = len(data)
        os_write = os.write
        fileno = self._fileno
        try:
            total_sent = os_write(fileno, data)
        except OSError, e:
            if get_errno(e) != errno.EAGAIN:
                raise IOError(*e.args)
            total_sent = 0

        while total_sent < len_data:
            wait_write(self)
            try:
                total_sent += os_write(fileno, data[total_sent:])
            except OSError, e:
                if get_errno(e) != errno. EAGAIN:
                    raise IOError(*e.args)

    def __del__ (self):
        try:
            os.close(self._fileno)
        except:
            # os.close may fail if __init__ didn't complete (i.e file dscriptor passed to popen was invalid
            pass

    def __repr__ (self):
        return "%s:%d" % (self.__class__.__name__, self._fileno)





def _operationOnClosedFile (*args, **kwargs):
    raise ValueError("I/O operation on closed file")



class UvFile(_fileobject):
    """
    UvFile is a cooperative replacement for file class.
    It will cooperate on pipes. It will block on regular file.

    Differences from file class:

    * mode is r/w property. Should re r/o
    * encoding property not implemented
    * write/writelines will not raise TypeError exception when non-string data is written
      it will write str(data) instead
    * Universal new lines are not supported and newlines property not implemented
    * file argument can be descriptor, file name or file object.
    """

    def __init__ (self, f, mode = 'r', bufsize = -1):
        if not isinstance(f, (basestring, int, file)):
            raise TypeError('f(ile) should be int, str, unicode or file, not %r' % f)

        if isinstance(f, basestring):
            f = open(f, mode, 0)

        if isinstance(f, int):
            fileno = f
            self._name = "<fd:%d>" % fileno
        else:
            fileno = os.dup(f.fileno())
            self._name = f.name
            if f.mode != mode:
                raise ValueError('file.mode %r does not match mode parameter %r' % (f.mode, mode))
            self._name = f.name
            f.close()

        super(UvFile, self).__init__(_UvSocketDuckForFd(fileno), mode, bufsize)
        set_nonblocking(self)
        self.softspace = 0

    @property
    def name (self): return self._name

    def __repr__ (self):
        return "<%s %s %r, mode %r at 0x%x>" % (
            self.closed and 'closed' or 'open',
            self.__class__.__name__,
            self.name,
            self.mode,
            (id(self) < 0) and (sys.maxint + id(self)) or id(self))

    def close (self):
        """
        Close the file

        :return: nothing
        """
        super(UvFile, self).close()
        for method in ['fileno', 'flush', 'isatty', 'next', 'read', 'readinto',
                       'readline', 'readlines', 'seek', 'tell', 'truncate',
                       'write', 'xreadlines', '__iter__', 'writelines']:
            setattr(self, method, _operationOnClosedFile)

    if getattr(file, '__enter__', None):
        def __enter__ (self):
            return self

        def __exit__ (self, *args):
            self.close()

    def xreadlines (self, buffer):
        return iter(self)

    def readinto (self, buf):
        data = self.read(len(buf))      ## TODO: could it be done without allocating intermediate?
        n = len(data)
        try:
            buf[:n] = data
        except TypeError, err:
            if not isinstance(buf, array.array):
                raise err
            buf[:n] = array.array('c', data)
        return n

    def _get_readahead_len (self):
        try:
            return len(self._rbuf.getvalue()) # StringIO in 2.5
        except AttributeError:
            return len(self._rbuf) # str in 2.4

    def _clear_readahead_buf (self):
        len = self._get_readahead_len()
        if len > 0:
            self.read(len)

    def tell (self):
        self.flush()
        try:
            return os.lseek(self.fileno(), 0, 1) - self._get_readahead_len()
        except OSError, e:
            raise IOError(*e.args)

    def seek (self, offset, whence = 0):
        self.flush()
        if whence == 1 and offset == 0: # tell synonym
            return self.tell()
        if whence == 1: # adjust offset by what is read ahead
            offset -= self.get_readahead_len()
        try:
            rv = os.lseek(self.fileno(), offset, whence)
        except OSError, e:
            raise IOError(*e.args)
        else:
            self._clear_readahead_buf()
            return rv

    if getattr(file, "truncate", None): # not all OSes implement truncate
        def truncate (self, size = -1):
            self.flush()
            if size == -1:
                size = self.tell()
            try:
                rv = os.ftruncate(self.fileno(), size)
            except OSError, e:
                raise IOError(*e.args)
            else:
                self.seek(size) # move position&clear buffer
                return rv

    def isatty (self):
        try:
            return os.isatty(self.fileno())
        except OSError, e:
            raise IOError(*e.args)

