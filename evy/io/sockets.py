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
import time

import socket
from socket import socket as _original_socket

from evy.support import get_errno

from evy.hubs import trampoline, wait_read, wait_write

from evy.io.sockets_uv import TcpSocket

from evy.io.utils import set_nonblocking, socket_accept, socket_connect, socket_checkerr
from evy.io.utils import _GLOBAL_DEFAULT_TIMEOUT
from evy.io.utils import SOCKET_BLOCKING, SOCKET_CLOSED
from evy.io.utils import _fileobject

from evy.timeout import Timeout
from evy.event import Event
from evy.green.dns import resolve_address

import pyuv
from evy.hubs import get_hub


BUFFER_SIZE = 4096



__all__ = ['GreenSocket']





def last_socket_error(code, msg = None):
    """
    Utility function for getting the last exception as a socket.error
    """
    if msg: msg += ': %s [%d]' % (pyuv.errno.strerror(code), code)
    else:   msg = '%s [%d]' % (pyuv.errno.strerror(code), code)

    return socket.error(code, msg)


class GenericSocket(object):

    EOF = (-1)

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None, **kwargs):
        """
        Initialize the UV socket

        :param family_or_realsock: a socket descriptor or a socket family
        """
        if isinstance(family, (int, long)): fd = _original_socket(family, type, proto, _sock)
        else:                               fd = family

        # import timeout from other socket, if it was there
        try:
            self._timeout = fd.gettimeout() or socket.getdefaulttimeout()
        except AttributeError:
            self._timeout = socket.getdefaulttimeout()

        set_nonblocking(fd)
        self.fd = fd

        if self.fd.type in [socket.SOCK_STREAM, socket.SOCK_DGRAM]:
            self.uv_hub = kwargs.get('uv_hub', get_hub())

            if 'uv_fd' in kwargs:
                self.uv_fd = kwargs['uv_fd']
            else:
                if self.fd.type == socket.SOCK_STREAM:  self.uv_fd = pyuv.TCP(self.uv_hub.uv_loop)
                elif self.fd.type == socket.SOCK_DGRAM: self.uv_fd = pyuv.UDP(self.uv_hub.uv_loop)
                else:                                   self.uv_fd = None

                if self.uv_fd:
                    fileno = self.fileno()
                    if fileno > 0:
                        self.uv_fd.open(fileno)

            if self.uv_fd:
                self.uv_fd.read_buffer = ''
                self.uv_fd.read_buffer_limit = 0




    # when client calls setblocking(0) or settimeout(0) the socket must act non-blocking
        self.act_non_blocking = False


    def close(self):
        if self.uv_fd:
            self.uv_hub.remove_descriptor(self.fileno(), skip_callbacks = True)
            self.uv_fd.close()
        #else:
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


    def bind(self, address):
        """
        Binds to a particular address and port

        :param address: the address
        """
        if self.uv_fd:
            assert self.uv_fd
            res = self.uv_fd.bind(resolve_address(address))
        else:
            self.fd.bind(address)


    def _uv_accept_callback(self, handle, error):
        """
        The callback invoked when we receive a connection request
        :param stream: the uv_stream handler for the server
        """
        if error:
            self.did_accept.send_exception(last_socket_error(error, msg = 'accept error'))
        else:
            try:
                ## create the handle for the newly accepted connection
                new_fd = pyuv.TCP(self.uv_hub.uv_loop)
                res = self.uv_fd.accept(new_fd)
                new_sock = GenericSocket(family = self.family, type = self.type, uv_hub = self.uv_hub, uv_fd = new_fd)
                new_sock_addr, _ = new_sock.getpeername()
                self.did_accept.send((new_sock, new_sock_addr))
            except pyuv.error.TCPError, e:
                code, msg = e.args
                self.did_accept.send_exception(last_socket_error(code, msg = 'accept error'))
            except Exception, e:
                self.did_accept.send_exception(e)

    def listen(self, backlog):
        if self.uv_fd:
            self.backlog = backlog
            assert self.backlog is not None
            if not self.uv_fd:
                raise socket.error(errno.EBADFD, 'invalid file descriptor')

            try:
                self.did_accept = Event()
                self.uv_fd.listen(self._uv_accept_callback)
            except pyuv.error.TCPError, e:
                print dir(e)
                raise socket.error(last_socket_error(0, msg = 'listen error'))
        else:
            self.fd.listen(backlog)

    def accept (self):
        if self.uv_fd:
            return self.did_accept.wait()        ## this could raise an exception...
        elif self.act_non_blocking:
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



    def connect (self, address):
        if self.uv_fd:
            did_connect = Event()

            def connect_callback(handle, error):
                try:
                    if error:  did_connect.send_exception(last_socket_error(error, msg = 'connect error'))
                    else:      did_connect.send(0)
                except Exception, e:
                    did_connect.send_exception(e)

            with Timeout(self.gettimeout(), socket.timeout("timed out")):
                self.uv_fd.connect(resolve_address(address), connect_callback)
                did_connect.wait()

        elif self.act_non_blocking:
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
        if self.uv_fd:
            try:
                did_connect = Event()

                def connect_callback(handle, error):
                    try:
                        if error:  did_connect.send_exception(last_socket_error(error, msg = 'connect error'))
                        else:      did_connect.send(0)
                    except Exception, e:
                        did_connect.send_exception(e)

                with Timeout(self.gettimeout(), socket.timeout("timed out")):
                    self.uv_fd.connect(address, connect_callback)
                    did_connect.wait()
            except Timeout:
                return errno.ETIME
            except socket.error, e:
                return e.errno

            return 0
        elif self.act_non_blocking:
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
        if self.act_non_blocking:
            return self.fd.recv(buflen, flags)
        elif self.uv_fd:
            tot_read = 0

            did_read = Event()
            self.uv_fd.read_buffer_limit = buflen

            def read_callback(handle, data, error):
                """
                The callback invoked when we read something from the socket
                """
                try:
                    if error:
                        if pyuv.errno.errorcode[error] == 'UV_EOF':
                            did_read.send(GenericSocket.EOF)
                        else:
                            did_read.send_exception(last_socket_error(error, msg = 'read error'))
                    elif data is None or len(data) == 0:
                        did_read.send(GenericSocket.EOF)
                    else:
                        ## append the data to the buffer and, maybe, stop reading...
                        handle.read_buffer += data

                        tot_len = len(handle.read_buffer)
                        if  tot_len >= self.uv_fd.read_buffer_limit:
                            did_read.send(tot_len)

                except Exception, e:
                    did_read.send_exception(e)

            try:
                with Timeout(self.gettimeout(), socket.timeout("timed out")):
                    res = self.uv_fd.start_read(read_callback)
                    tot_read = did_read.wait()
                    if tot_read == GenericSocket.EOF or tot_read >= buflen:
                        self.uv_fd.stop_read()

                    ## get the data we want from the read buffer, and keep the rest
                    res = self.uv_fd.read_buffer[:buflen]
                    self.uv_fd.read_buffer = self.uv_fd.read_buffer[buflen:]
            except:
                self.uv_fd.stop_read()
                raise

            return res
        else:
            fd = self.fd
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

        return self.fd.recvfrom(*args)

    def recvfrom_into (self, *args):
        if not self.act_non_blocking:
            wait_read(self.fd, self.gettimeout(), socket.timeout("timed out"))

        return self.fd.recvfrom_into(*args)

    def recv_into (self, *args):
        if not self.act_non_blocking:
            wait_read(self.fd, self.gettimeout(), socket.timeout("timed out"))

        return self.fd.recv_into(*args)


    def send (self, data, flags = 0):
        total_sent = 0

        if self.act_non_blocking:
            total_sent = self.fd.send(data, flags)
        elif self.uv_fd:

            did_write = Event()
            write_len = len(data)

            def write_callback(handle, error):
                """
                The callback invoked when we are done writting to the socket
                """
                try:
                    ## free the write request and the temporal buffer used for sending
                    if error:           did_write.send_exception(last_socket_error(error, msg = 'write error'))
                    else:               did_write.send(write_len)
                except Exception, e:    did_write.send_exception(e)

            with Timeout(self.gettimeout(), socket.timeout("timed out")):
                self.uv_fd.write(data, write_callback)
                total_sent = did_write.wait()
                ## TODO: check if the connection has been broken, etc...

        else:
            fd = self.fd
            # blocking socket behavior - sends all, blocks if the buffer is full
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

        assert not hasattr(self, 'did_write')
        assert not hasattr(self, 'uv_write_len')

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

    def getsockname(self):
        if self.uv_fd:
            return self.uv_fd.getsockname()
        else:
            return self.fd.getsockname()

    def getpeername(self):
        if self.uv_fd:
            return self.uv_fd.getpeername()
        else:
            return self.fd.getpeername()

    def ioctl(self, *args):
        pass

    def shutdown(self, *args):
        """
        Shut down one or both halves of the connection. If how is SHUT_RD, further receives are
        disallowed. If how is SHUT_WR, further sends are disallowed. If how is SHUT_RDWR, further
        sends and receives are disallowed. Depending on the platform, shutting down one half of
        the connection can also close the opposite half (e.g. on Mac OS X, shutdown(SHUT_WR) does
        not allow further reads on the other end of the connection).
        :param args:
        :return:
        """
        if self.uv_fd:
            if not self.uv_fd:
                raise socket.error(errno.EBADFD, 'invalid file descriptor')

            shudown_event = Event()
            def _shutdown_callback(tcp_handle, error):
                shudown_event.send()

            self.uv_fd.shutdown(_shutdown_callback)
            shudown_event.wait()
        else:
            self.fd.shutdown(*args)



####################################################################################################


_DELEGATE_METHODS = (
    "accept",
    "bind",
    "connect",
    "connect_ex",
    "close",
    "fileno",
    "gettimeout",
    "getpeername",
    "getsockname",
    "getsockopt",
    "ioctl",
    "makefile",
    "listen",
    "recv",
    "recvfrom",
    "recv_into",
    "recvfrom_into",
    "send",
    "sendto",
    "shutdown",
    "setsockopt"
    )


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

#        if isinstance(family, (int, long)):
#            if type == socket.SOCK_STREAM:
#                self.delegate = TcpSocket(family, type, proto, _sock)
#
#        elif isinstance(family, _original_socket):
#            _sock = family
#
#            family = _sock .family
#            type = _sock.type
#            proto = _sock.proto
#
#            if type == socket.SOCK_STREAM:
#                self.delegate = TcpSocket(family, type, proto, _sock)
#
#        if not self.delegate:
#            self.delegate = GenericSocket(family, type, proto, _sock)
#
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







def shutdown_safe (sock):
    """
    Shuts down the socket. This is a convenience method for
    code that wants to gracefully handle regular sockets, SSL.Connection
    sockets from PyOpenSSL and ssl.SSLSocket objects from Python 2.6
    interchangeably.  Both types of ssl socket require a shutdown() before
    close, but they have different arity on their shutdown method.

    Regular sockets don't need a shutdown before close, but it doesn't hurt.
    """
    try:
        try:
            # socket, ssl.SSLSocket
            return sock.shutdown(socket.SHUT_RDWR)
        except TypeError:
            # SSL.Connection
            return sock.shutdown()
    except socket.error, e:
        # we don't care if the socket is already closed;
        # this will often be the case in an http server context
        if get_errno(e) != errno.ENOTCONN:
            raise

