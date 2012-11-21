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

import array
import errno
import os
import socket
from socket import socket as _original_socket
import sys
import time

from evy.support import get_errno
from evy.support import greenlets as greenlet

from evy.hubs import trampoline, wait_read, wait_write
from evy.hubs import get_hub

from evy.uv.interface import libuv, ffi, handle_is_active, cast_to_handle
from evy import timeout


__all__ = ['UvSocket']


BUFFER_SIZE         = 4096
CONNECT_ERR         = set((errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK))
CONNECT_SUCCESS     = set((0, errno.EISCONN))

if sys.platform[:3] == "win":
    CONNECT_ERR.add(errno.WSAEINVAL)   # Bug 67



# Emulate _fileobject class in 3.x implementation
# Eventually this internal socket structure could be replaced with makefile calls.
try:
    _fileobject = socket._fileobject
except AttributeError:
    def _fileobject (sock, *args, **kwargs):
        return _original_socket.makefile(sock, *args, **kwargs)



def socket_connect (descriptor, address):
    """
    Attempts to connect to the address, returns the descriptor if it succeeds,
    returns None if it needs to trampoline, and raises any exceptions.
    """
    err = descriptor.connect_ex(address)
    if err in CONNECT_ERR:
        return None
    if err not in CONNECT_SUCCESS:
        raise socket.error(err, errno.errorcode[err])
    return descriptor


def socket_checkerr (descriptor):
    err = descriptor.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
    if err not in CONNECT_SUCCESS:
        raise socket.error(err, errno.errorcode[err])


def socket_accept (descriptor):
    """
    Attempts to accept() on the descriptor, returns a client,address tuple
    if it succeeds; returns None if it needs to trampoline, and raises
    any exceptions.
    """
    try:
        return descriptor.accept()
    except socket.error, e:
        if get_errno(e) == errno.EWOULDBLOCK:
            return None
        raise


if sys.platform[:3] == "win":
    # winsock sometimes throws ENOTCONN
    SOCKET_BLOCKING = set((errno.EWOULDBLOCK,))
    SOCKET_CLOSED   = set((errno.ECONNRESET, errno.ENOTCONN, errno.ESHUTDOWN))
else:
    # oddly, on linux/darwin, an unconnected socket is expected to block,
    # so we treat ENOTCONN the same as EWOULDBLOCK
    SOCKET_BLOCKING = set((errno.EWOULDBLOCK, errno.ENOTCONN))
    SOCKET_CLOSED   = set((errno.ECONNRESET, errno.ESHUTDOWN, errno.EPIPE))




def set_nonblocking (fd):
    """
    Sets the descriptor to be nonblocking.  Works on many file-like objects as well as sockets.
    Only sockets can be nonblocking on Windows, however.
    """
    try:
        setblocking = fd.setblocking
    except AttributeError:
        # fd has no setblocking() method. It could be that this version of
        # Python predates socket.setblocking(). In that case, we can still set
        # the flag "by hand" on the underlying OS fileno using the fcntl
        # module.
        try:
            import fcntl
        except ImportError:
            # Whoops, Windows has no fcntl module. This might not be a socket
            # at all, but rather a file-like object with no setblocking()
            # method. In particular, on Windows, pipes don't support
            # non-blocking I/O and therefore don't have that method. Which
            # means fcntl wouldn't help even if we could load it.
            raise NotImplementedError("set_nonblocking() on a file object "
                                      "with no setblocking() method "
                                      "(Windows pipes don't support non-blocking I/O)")
            # We managed to import fcntl.
        fileno = fd.fileno()
        flags = fcntl.fcntl(fileno, fcntl.F_GETFL)
        fcntl.fcntl(fileno, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    else:
        # socket supports setblocking()
        setblocking(0)


try:
    from socket import _GLOBAL_DEFAULT_TIMEOUT
except ImportError:
    _GLOBAL_DEFAULT_TIMEOUT = object()


####################################################################################################


class UvSocket(object):
    """
    libUV version of socket.socket class, that is intended to be 100% API-compatible.
    """

    def __init__ (self, family_or_realsock = socket.AF_INET, *args, **kwargs):
        """
        Initialize the UV socket

        :param family_or_realsock: a socket descriptor or a socket family
        """
        hub = get_hub()

        if isinstance(family_or_realsock, (int, long)):
            fd = _original_socket(family_or_realsock, *args, **kwargs)
        else:
            fd = family_or_realsock
            assert not args, args
            assert not kwargs, kwargs

        # import timeout from other socket, if it was there
        try:
            self._timeout = fd.gettimeout() or socket.getdefaulttimeout()
        except AttributeError:
            self._timeout = socket.getdefaulttimeout()

        set_nonblocking(fd)
        self.fd = fd

        ## setup the UV handle from the file descriptor
        assert self.fd.fileno() > 0
        fileno = self.fd.fileno()
        self.handle = None
        if self._is_tcp():
            self.handle = ffi.new('struct uv_tcp_s*')
            libuv.uv_tcp_init(hub.ptr, self.handle)
            libuv.uv_tcp_open(self.handle, fileno)
        elif self._is_udp():
            self.handle = ffi.new('struct uv_udp_s*')
            libuv.uv_udp_init(hub.ptr, self.handle)
            libuv.uv_udp_open(self.handle, fileno)
        else:
            raise RuntimeError('unsupported socket type')

        # when client calls setblocking(0) or settimeout(0) the socket must act non-blocking
        self.act_non_blocking = False


    def close(self):
        fd = self.fd

        def closed_callback(handle):
            fd.close()

        if self.handle:
            uv_handle = cast_to_handle(self.handle)

            ## we must remove all pollers on this socket
            get_hub().remove_descriptor(self.fileno(), skip_callbacks = True)

            if not libuv.uv_is_closing(uv_handle):
                _closed_callback = ffi.callback('void(*)(uv_handle_t*)', closed_callback)
                libuv.uv_close(uv_handle, _closed_callback)
                self.handle = None

    @property
    def _sock (self):
        return self

    def _is_tcp(self):   return self.fd.type is socket.SOCK_STREAM

    def _is_udp(self):   return self.fd.type is socket.SOCK_DGRAM

    def __getattr__ (self, name):
        """
        Forward unknown attibutes to fd, caching the value for future use.

        :param name: the attribute
        :return: the value for that attribute
        """

        # I do not see any simple attribute which could be changed
        # so caching everything in self is fine,
        # If we find such attributes - only attributes having __get__ might be cahed.
        # For now - I do not want to complicate it.

        attr = getattr(self.fd, name)
        setattr(self, name, attr)
        return attr


    def accept (self):
        if self.act_non_blocking:
            return self.fd.accept()
        else:
            fd = self.fd
            while True:
                res = socket_accept(fd)
                if not res:
                    wait_read(fd, self.gettimeout(), socket.timeout("timed out"))
                else:
                    client, addr = res
                    set_nonblocking(client)
                    return type(self)(client), addr



    def _connect_tcp(self):
        t = None
        hub = get_hub()
        current = greenlet.getcurrent()
        new_conn = None
        errors = None

        assert hub.greenlet is not current, 'do not call blocking functions from the mainloop'

        if timeout is not None:
            t = hub.schedule_call_global(self.gettimeout(), current.throw, socket.timeout("timed out"))

        ## the callback function when we are connected
        def _connect_callback(req, status):
            assert req.data is self
            if status < 0:
                errors = 1      ## TODO
            current.switch()
        connect_cb = ffi.callback("void(uv_connect_t* req, int status)", _connect_callback)

        try:
            req = ffi.new('uv_connect_t*')
            req.data = self
            address = ffi.new('struct sockaddr_in')
            libuv.uv_tcp_connect(req, self.handle, address, connect_cb)
            return hub.switch()
        finally:
            if t is not None:
                t.cancel()

        if errors is not None:
            raise socket.error(1, None)       ## TODO

        return


    def connect (self, address):
        if self.act_non_blocking:
            return self.fd.connect(address)
        else:
            fd = self.fd
            if self.gettimeout() is None:
                while not socket_connect(fd, address):
                    trampoline(fd, write = True)
                    socket_checkerr(fd)
            else:
                end = time.time() + self.gettimeout()
                while True:
                    if socket_connect(fd, address):
                        return
                    if time.time() >= end:
                        raise socket.timeout("timed out")
                    wait_write(fd, end - time.time(), socket.timeout("timed out"))
                    socket_checkerr(fd)

    def connect_ex (self, address):
        if self.act_non_blocking:
            return self.fd.connect_ex(address)
        else:
            fd = self.fd
            if self.gettimeout() is None:
                while not socket_connect(fd, address):
                    try:
                        trampoline(fd, write = True)
                        socket_checkerr(fd)
                    except socket.error, ex:
                        return get_errno(ex)
            else:
                end = time.time() + self.gettimeout()
                while True:
                    try:
                        if socket_connect(fd, address):
                            return 0
                        if time.time() >= end:
                            raise socket.timeout(errno.EAGAIN)
                        wait_write(fd, end - time.time(), socket.timeout(errno.EAGAIN))
                        socket_checkerr(fd)
                    except socket.error, ex:
                        return get_errno(ex)

    def dup (self, *args, **kw):
        sock = self.fd.dup(*args, **kw)
        set_nonblocking(sock)
        newsock = type(self)(sock)
        newsock.settimeout(self.gettimeout())
        return newsock

    def makefile (self, *args, **kw):
        return _fileobject(self.dup(), *args, **kw)

    def recv (self, buflen, flags = 0):
        fd = self.fd
        if self.act_non_blocking:
            return fd.recv(buflen, flags)
        else:
            while True:
                try:
                    return fd.recv(buflen, flags)
                except socket.error, e:
                    if get_errno(e) in SOCKET_BLOCKING:
                        pass
                    elif get_errno(e) in SOCKET_CLOSED:
                        return ''
                    else:
                        raise
                wait_read(fd, self.gettimeout(), socket.timeout("timed out"))

    def recvfrom (self, *args):
        if not self.act_non_blocking:
            wait_read(self.fd, self.gettimeout(), socket.timeout("timed out"))
        else:
            return self.fd.recvfrom(*args)

    def recvfrom_into (self, *args):
        if not self.act_non_blocking:
            wait_read(self.fd, self.gettimeout(), socket.timeout("timed out"))
        else:
            return self.fd.recvfrom_into(*args)

    def recv_into (self, *args):
        if not self.act_non_blocking:
            wait_read(self.fd, self.gettimeout(), socket.timeout("timed out"))
        else:
            return self.fd.recv_into(*args)

    def send (self, data, flags = 0):
        fd = self.fd
        if self.act_non_blocking:
            return fd.send(data, flags)
        else:
            # blocking socket behavior - sends all, blocks if the buffer is full
            total_sent = 0
            len_data = len(data)

            while 1:
                try:
                    total_sent += fd.send(data[total_sent:], flags)
                except socket.error, e:
                    if get_errno(e) not in SOCKET_BLOCKING:
                        raise

                if total_sent == len_data:
                    break

                wait_write(self.fd, self.gettimeout(), socket.timeout("timed out"))

            return total_sent

    def sendall (self, data, flags = 0):
        tail = self.send(data, flags)
        len_data = len(data)
        while tail < len_data:
            tail += self.send(data[tail:], flags)

    def sendto (self, *args):
        wait_write(self.fd)
        return self.fd.sendto(*args)

    def setblocking (self, flag):
        if flag:
            self.act_non_blocking = False
            self._timeout = None
        else:
            self.act_non_blocking = True
            self._timeout = 0.0

    def settimeout (self, howlong):
        if howlong is None or howlong == _GLOBAL_DEFAULT_TIMEOUT:
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




