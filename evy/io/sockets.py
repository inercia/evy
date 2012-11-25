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
from ImageChops import add

import errno
import time

import socket
from socket import socket as _original_socket

from evy.support import get_errno

from evy.hubs import trampoline, wait_read, wait_write
from evy.hubs import get_hub

from evy.uv.sockets import TcpSocket

from evy.io.utils import set_nonblocking, socket_accept, socket_connect, socket_checkerr
from evy.io.utils import _GLOBAL_DEFAULT_TIMEOUT
from evy.io.utils import SOCKET_BLOCKING, SOCKET_CLOSED
from evy.io.utils import _fileobject



__all__ = ['GreenSocket']






class GenericSocket(object):

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None):
        """
        Initialize the UV socket

        :param family_or_realsock: a socket descriptor or a socket family
        """
        self.uv_fd = None

        if isinstance(family, (int, long)):
            fd = _original_socket(family, type, proto, _sock)
        else:
            fd = family

        # import timeout from other socket, if it was there
        try:
            self._timeout = fd.gettimeout() or socket.getdefaulttimeout()
        except AttributeError:
            self._timeout = socket.getdefaulttimeout()

        set_nonblocking(fd)
        self.fd = fd

        # when client calls setblocking(0) or settimeout(0) the socket must act non-blocking
        self.act_non_blocking = False


    def close(self):
        if self.uv_fd:
            self.uv_fd.close()
        else:
            self.fd.close()

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
        if self.uv_fd:
            self.uv_fd.accept()
        else:
            if self.act_non_blocking:
                return self.fd.accept()

            fd = self.fd
            while True:
                res = socket_accept(fd)
                if not res:
                    wait_read(fd, self.gettimeout(), socket.timeout("timed out"))
                else:
                    client, addr = res
                    set_nonblocking(client)
                    return type(self)(client), addr

    def connect (self, address):
        if self.uv_fd:
            self.uv_fd.connect(address)
        else:
            if self.act_non_blocking:
                return self.fd.connect(address)

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
        if self.uv_fd:
            self.uv_fd.connect_ex(address)
        else:
            if self.act_non_blocking:
                return self.fd.connect_ex(address)
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






####################################################################################################


_DELEGATE_METHODS = (
    "accept",
    "bind",
    "connect",
    "connect_ex",
    "gettimeout",
    "getpeername",
    "getsockname",
    "getsockopt",
    "listen",
    "recv",
    "recvfrom",
    "recv_into",
    "recvfrom_into",
    "send",
    "sendto",
    "setsockopt")


class GreenSocket(object):
    """
    libUV version of socket.socket class, that is intended to be 100% API-compatible.
    """

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None):
        """
        Initialize the UV socket

        :param family_or_realsock: a socket descriptor or a socket family
        """
        self.delegate = None


        if isinstance(family, (int, long)):
            if type == socket.SOCK_STREAM:
                self.delegate = TcpSocket(family, type, proto, _sock)

        elif isinstance(family, _original_socket):
            _sock = family

            family = _sock .family
            type = _sock.type
            proto = _sock.proto

            if type == socket.SOCK_STREAM:
                self.delegate = TcpSocket(family, type, proto, _sock)

        if not self.delegate:
            self.delegate = GenericSocket(family, type, proto, _sock)

        for method in _DELEGATE_METHODS :
            setattr(self, method, getattr(self.delegate, method))

        # import timeout from other socket, if it was there
        try:
            self._timeout = self.delegate.gettimeout() or socket.getdefaulttimeout()
        except AttributeError:
            self._timeout = socket.getdefaulttimeout()

        ##set_nonblocking(self.delegate)

        # when client calls setblocking(0) or settimeout(0) the socket must act non-blocking
        self.act_non_blocking = False


    @property
    def _sock (self):
        return self

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

        attr = getattr(self.delegate, name)
        setattr(self, name, attr)
        return attr

