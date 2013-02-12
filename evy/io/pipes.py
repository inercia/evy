#
# Evy - a concurrent networking library for Python
#
# Unless otherwise noted, the files in Evy are under the following MIT license:
#
# Copyright (c) 2012, Alvaro Saurin
# Copyright (c) 2008-2010, Eventlet Contributors (see AUTHORS)
# Copyright (c) 2007-2010, Linden Research, Inc.
# Copyright (c) 2005-2006, Bob Ippolito
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

import pyuv

import sys
import array

from weakref import proxy

import socket
from socket import socket as _original_socket

from evy.support import get_errno
from evy.hubs import get_hub
from evy.hubs import wait_read, wait_write
from evy.event import Event
from evy.io.utils import set_nonblocking
from evy.patcher import original
from evy.support.errors import last_file_error

import errno

_os_orig = original("os")


# Emulate _fileobject class in 3.x implementation
# Eventually this internal socket structure could be replaced with makefile calls.
try:
    _fileobject = socket._fileobject
except AttributeError:
    def _fileobject (sock, *args, **kwargs):
        return _original_socket.makefile(sock, *args, **kwargs)



__all__ = []




class _SocketDuckForFd(object):
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
                data = _os_orig.read(self._fileno, buflen)
                return data
            except OSError, e:
                if get_errno(e) != errno.EAGAIN:
                    raise IOError(*e.args)
            wait_read(self)

    def sendall (self, data):
        len_data = len(data)
        os_write = _os_orig.write
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
            _os_orig.close(self._fileno)
        except:
            # os.close may fail if __init__ didn't complete (i.e file dscriptor passed to popen was invalid
            pass

    def __repr__ (self):
        return "%s:%d" % (self.__class__.__name__, self._fileno)





def _operationOnClosedFile (*args, **kwargs):
    raise ValueError("I/O operation on closed file")



class GreenPipe(_fileobject):
    """
    GreenPipe is a cooperative replacement for file class.
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

        self.uv_hub = proxy(get_hub())

        if not isinstance(f, (basestring, int, file)):
            raise TypeError('f(ile) should be int, str, unicode or file, not %r' % f)

        if isinstance(f, basestring):
            self._path = f
            f = open(f, mode, 0)
            fileno = f.fileno()

        if isinstance(f, int):
            fileno = f
            self._name = "<fd:%d>" % fileno
            self._path = None
        else:
            fileno = _os_orig.dup(f.fileno())
            self._name = self._path = f.name
            if f.mode != mode:
                raise ValueError('file.mode %r does not match mode parameter %r' % (f.mode, mode))
            f.close()       ## close the file provided: we keep our dupped version...

        assert isinstance(fileno, int)
        self._fileobj = _os_orig.fdopen(fileno, mode)
        
        super(GreenPipe, self).__init__(_SocketDuckForFd(fileno), mode, bufsize)
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
        #super(GreenPipe, self).close()
        self._fileobj.close()
        for method in ['fileno', 'flush', 'isatty', 'next', 'read', 'readinto',
                       'readline', 'readlines', 'seek', 'tell', 'truncate',
                       'write', 'xreadlines', '__iter__', 'writelines']:
            setattr(self, method, _operationOnClosedFile)

    def fileno(self):
        return self._fileobj.fileno()
        
    if getattr(file, '__enter__', None):
        def __enter__ (self):
            return self

        def __exit__ (self, *args):
            self.close()

    def read(self, rlen):
        did_read = Event()
        def read_callback(loop, path, read_data, errorno):
            if errorno:
                did_read.send_exception(last_file_error(errorno, 'read error on fd:%d' % self.fileno()))
            else:
                did_read.send(read_data)

        roffset = self._fileobj.tell()            
        pyuv.fs.read(self.uv_hub.ptr, self.fileno(), rlen, roffset, read_callback)
        return did_read.wait()
        
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

    def tell (self):
        self.flush()
        return self._fileobj.tell()

    def seek (self, offset, whence = 0):
        self.flush()
        if whence == 1 and offset == 0: # tell synonym
            return self.tell()
        try:
            rv = _os_orig.lseek(self.fileno(), offset, whence)
        except OSError, e:
            raise IOError(*e.args)
        else:
            return rv

    if getattr(file, "truncate", None): # not all OSes implement truncate
        def truncate (self, size = -1):
            self.flush()
            if size == -1:
                size = self.tell()
            try:
                rv = _os_orig.ftruncate(self.fileno(), size)
            except OSError, e:
                raise IOError(*e.args)
            else:
                self.seek(size) # move position&clear buffer
                return rv

    def isatty (self):
        try:
            return _os_orig.isatty(self.fileno())
        except OSError, e:
            raise IOError(*e.args)

