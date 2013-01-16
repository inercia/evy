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

import errno
import socket
from socket import socket as _original_socket


from evy.hubs import get_hub
from evy.timeout import Timeout
from evy.event import Event
from evy.green.dns import resolve_address


import pyuv


# Emulate _fileobject class in 3.x implementation
# Eventually this internal socket structure could be replaced with makefile calls.
try:
    _fileobject = socket._fileobject
except AttributeError:
    def _fileobject (sock, *args, **kwargs):
        return _original_socket.makefile(sock, *args, **kwargs)


__all__ = [
    'TcpSocket',
    ]



def last_socket_error(code, msg = None):
    """
    Utility function for getting the last exception as a socket.error
    """
    if msg: msg += ': %s [%d]' % (pyuv.errno.strerror(code), code)
    else:   msg = '%s [%d]' % (pyuv.errno.strerror(code), code)

    return socket.error(code, msg)


####################################################################################################

class BaseSocket(object):

    EOF = (-1)

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None, **kwargs):
        """
        Initialize the socket
        """
        self.family = family
        self.type = type
        self.proto = proto

        self.uv_handle = kwargs.get('uv_handle', None)
        self.uv_hub = kwargs.get('uv_hub', get_hub())

        if _sock:
            self.uv_fileno = _sock.fileno()
            self._timeout = _sock.gettimeout()
        else:
            self.uv_fileno = None
            self._timeout = socket.getdefaulttimeout()

        # when client calls setblocking(0) or settimeout(0) the socket must act non-blocking
        self.act_non_blocking = False


    def _uv_closed_callback(self, handle):
        self.uv_handle = None
        self.uv_fileno = None

    def close(self):
        if self.uv_handle:
            ## we must remove all pollers on this socket
            if self.uv_fileno:
                get_hub().remove_descriptor(self.uv_fileno, skip_callbacks = True)

            if not self.uv_handle.closed:
                self.uv_handle.close(self._uv_closed_callback)


    @property
    def _sock (self):
        return self


    def dup (self, *args, **kw):
        sock = self.fd.dup(*args, **kw)
        #set_nonblocking(sock)
        newsock = type(self)(sock)
        newsock.settimeout(self.gettimeout())
        return newsock

    def fileno(self):
        ## TODO
        raise RuntimeError('not implemented')

    def ioctl(self, control, option):
        ## TODO
        raise RuntimeError('not implemented')

    def makefile (self, *args, **kw):
        """
        Return a file object associated with the socket.
        The file object references a dup()ped version of the socket file descriptor, so the file
        object and socket object may be closed or garbage-collected independently. The socket
        must be in blocking mode (it can not have a timeout). The optional mode and bufsize
        arguments are interpreted the same way as by the built-in file() function.

        Note: On Windows, the file-like object created by makefile() cannot be used where a file
        object with a file descriptor is expected, such as the stream arguments of subprocess.Popen().

        :param args: mode and buffer size
        :param kw:
        :return: a file objet
        """
        return _fileobject(self.dup(), *args, **kw)

    def setblocking (self, flag):
        if flag:
            self.act_non_blocking = False
            self._timeout = None
        else:
            self.act_non_blocking = True
            self._timeout = 0.0

    def settimeout (self, howlong):
        if howlong is None: #or howlong == _GLOBAL_DEFAULT_TIMEOUT:  ## TODO
            self.setblocking(True)
            return
        else:
            try:
                f = howlong.__float__
            except AttributeError:
                raise TypeError('a float is required')
            howlong = f()
            if howlong < 0.0:
                raise ValueError('Timeout value out of range')
            if howlong == 0.0:
                self.setblocking(howlong)
            else:
                self._timeout = howlong

    def gettimeout (self):
        return self._timeout

    def getsockopt(self, level, optname, buflen = None):
        pass


    @property
    def closing(self):
        """
        Used to determine whether a socket is closing or closed.

        It is only valid between the initialization of the handle and the arrival of the close
        callback, and cannot be used to validate the handle.

        :return: True if the socket is closed or being closed
        """
        if self.uv_handle:  return self.uv_handle.closing
        else:               return True


####################################################################################################

class TcpSocket(BaseSocket):
    """
    libUV version of a Tcp (V4 or V6) socket
    """

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None, **kwargs):
        """
        Initialize the socket
        """
        super(TcpSocket, self).__init__(family, type, proto, _sock, **kwargs)

        assert hasattr(self, 'uv_handle')
        if not self.uv_handle:
            self.uv_handle = pyuv.TCP(self.uv_hub.uv_loop)

            if self.uv_fileno:
                self.uv_handle.open(self.uv_fileno)

            assert self.uv_handle is not None

        self.backlog = None

        # some events
        self.did_accept = Event()
        self.did_connect = Event()
        self.did_read = Event()

