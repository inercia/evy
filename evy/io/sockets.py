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

import errno
import time

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import socket
from socket import socket as _original_socket

import weakref
import pyuv

from evy.support import get_errno
from evy.support.errors import last_socket_error

from evy.hubs import trampoline, wait_read, wait_write
from evy.hubs import get_hub
from evy.timeout import Timeout
from evy.event import Event
from evy.green.dns import resolve_address

from evy.io.utils import set_nonblocking, socket_accept, socket_connect, socket_checkerr
from evy.io.utils import _GLOBAL_DEFAULT_TIMEOUT
from evy.io.utils import SOCKET_BLOCKING, SOCKET_CLOSED
from evy.io.utils import _fileobject


__all__ = [
    'GreenSocket',
]

BUFFER_SIZE = 4096


# Emulate _fileobject class in 3.x implementation
# Eventually this internal socket structure could be replaced with makefile calls.
try:
    _fileobject = socket._fileobject
except AttributeError:
    def _fileobject (sock, *args, **kwargs):
        return _original_socket.makefile(sock, *args, **kwargs)



####################################################################################################

def _closed_dummy (*args):
    raise socket.error(errno.EBADF, 'Bad file descriptor')

# All the method names that must be delegated to either the real socket
# object or the _closedsocket object.
_closed_delegate_methods = ("recv", "recvfrom", "recv_into", "recvfrom_into", "send", "sendto")

####################################################################################################


class GreenSocket(object):
    """
    libUV version of socket.socket class, that is intended to be 100% API-compatible.
    """

    EOF = (-1)

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None,
                  _hub = None):
        """
        Initialize the UV socket

        :param family_or_realsock: a socket descriptor or a socket family
        """
        self.uv_fd = None
        self.uv_handle = None
        self.uv_hub = None
        self.uv_recv_string = ''                    # buffer for receiving data...

        if isinstance(family, (int, long)):
            self.uv_fd = _original_socket(family, type, proto, _sock)
        elif isinstance(family, GreenSocket):
            _sock = family
            self.uv_fd = _sock.uv_fd
            if hasattr(_sock, 'uv_hub') and _sock.uv_hub:
                _hub = _sock.uv_hub
        else:
            _sock = family
            self.uv_fd = _sock

        if not self.uv_hub:
            if _hub:
                self.uv_hub = _hub
            else:
                self.uv_hub = weakref.proxy(get_hub())

        ## check if the socket type is supported by pyUV and we can create a pyUV socket...
        if not self.uv_handle:
            if self.type == socket.SOCK_STREAM:
                self.uv_handle = pyuv.TCP(self.uv_hub.uv_loop)
                self.uv_handle.open(self.fileno())
            elif self.type == socket.SOCK_DGRAM:
                self.uv_handle = pyuv.UDP(self.uv_hub.uv_loop)
                self.uv_handle.open(self.fileno())

        # import timeout from other socket, if it was there
        try:
            self._timeout = self.uv_fd.gettimeout() or socket.getdefaulttimeout()
        except AttributeError:
            self._timeout = socket.getdefaulttimeout()

        assert self.uv_fd, 'the socket descriptor must be not null'

        set_nonblocking(self.uv_fd)

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
        attr = getattr(self.uv_fd, name)
        setattr(self, name, attr)
        return attr


    def __repr__ (self):
        try:
            uv = 'yes' if self.uv_handle else 'no'
            blk = 'no' if self.act_non_blocking else 'no'
            retval = "<GreenSocket object at %s (fd:%d, uv:%s, blk:%s)>" % (
            hex(id(self)), self.fileno(), uv, blk)
            return retval
        except:
            return '<GreenSocket>'


    def __del__ (self):
        ## force the close() method invokation when the refcount reaches 0
        self.close()

    def close (self):
        """
        Close the TCP socket
        :return: None
        """
        try:
            if self.uv_handle:
                ## remove some TCP-specific stuff
                self._did_listen = None
                self._did_accept = None

                if not self.uv_handle.closed:
                    def closed_callback (*args):
                        pass
                    self.uv_handle.close(closed_callback)

            elif self.uv_fd:
                self.uv_fd.close()
        finally:
            ## we must remove all pollers on this socket
            hub = self.uv_hub if self.uv_hub else get_hub()
            hub.remove_descriptor(self.fileno(), skip_callbacks = True)

            self.uv_handle = None
            self.uv_fd = None

            # This function should not reference any globals. See issue #808164.
            for method in _closed_delegate_methods:
                setattr(self, method, _closed_dummy)


    @property
    def closed (self):
        """
        Used to determine whether a socket is closed.

        It is only valid between the initialization of the handle and the arrival of the close
        callback, and cannot be used to validate the handle.

        :return: True if the socket is closed or being closed
        """
        if self.uv_handle:
            try:
                return self.uv_handle.closed
            except AttributeError:
                pass
            return True
        else:
            raise RuntimeError('not implemented')


    def dup (self, *args, **kw):
        sock = self.uv_fd.dup(*args, **kw)
        set_nonblocking(sock)
        newsock = type(self)(sock)
        newsock.settimeout(self.gettimeout())

        #if self.uv_handle:
        #    new_handle = pyuv.TCP(self.uv_hub.uv_loop)
        #    return GreenSocket(family = socket.AF_INET, type = socket.SOCK_STREAM, uv_hub = self.uv_hub, uv_handle = new_handle)

        return newsock


    def bind (self, address):
        """
        Binds to a particular address and port
        :param address: the address, as a pair of IP and port
        """
        if not self.uv_handle:
            return self.uv_fd.bind(address)
        else:
            try:
                self.uv_handle.bind(resolve_address(address))
            except ValueError, e:
                raise OverflowError(e)
            except pyuv.error.TCPError, e:
                raise socket.error(*last_socket_error(e.args[0], msg = 'bind error'))


    def listen (self, backlog):
        """
        Listen for a new connection
        :param backlog: the backlog
        """
        ## note: we cannot use the pyUV listne()/accept() as we would lose the reference to the
        ## underlying 'python socket', and then we could not dup()/fileno()/etc...
        return self.uv_fd.listen(backlog)

    def accept (self):
        """
        Accept a new connection when we are listening
        :return: a socket and remote address pair
        """
        if self.act_non_blocking:
            return self.uv_fd.accept()
        else:
            fd = self.uv_fd
            while True:
                res = socket_accept(fd)
                if not res:
                    wait_read(fd, self.gettimeout(), socket.timeout("timed out"))
                else:
                    client, addr = res
                    set_nonblocking(client)
                    return GreenSocket(client, _hub = self.uv_hub), addr


    def connect (self, address):
        """
        Connects to a remote address
        :param address: the remote address, as a IP and port tuple
        """
        if self.act_non_blocking:
            return self.uv_fd.connect(address)
        elif self.uv_handle:
            try:
                did_connect = Event()

                def connect_callback (tcp_handle, error):
                    try:
                        if error:
                            did_connect.send_exception(
                                last_socket_error(error, msg = 'connect error'))
                        else:
                            did_connect.send(0)
                    except Exception, e:
                        did_connect.send_exception(e)

                self.uv_handle.connect(resolve_address(address), connect_callback)
                did_connect.wait(self.gettimeout(), socket.timeout(errno.ETIME, "timed out"))
            except pyuv.error.TCPError, e:
                raise socket.error(*last_socket_error(e.args[0], msg = 'connect error'))
        else:
            fd = self.uv_fd
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
        """
        Connects to a remote address not raising exceptions
        :param address: the remote address, as a IP and port tuple
        :return: 0 if successful, or an error code otherwise
        """
        if self.act_non_blocking:
            return self.uv_fd.connect_ex(address)
        elif self.uv_handle:
            try:
                self.connect(address)
                return 0
            except (socket.timeout, Timeout):
                return errno.ETIME
            except pyuv.error.TCPError, e:
                raise socket.error(*last_socket_error(e.args[0], msg = 'connect error'))
            except Exception, e:
                code = e.args[0]
                return code
        else:
            fd = self.uv_fd
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

    def ioctl (self, *args):
        self.uv_fd.ioctl(*args)

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

    def recvfrom (self, *args):
        if not self.uv_fd:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        if not self.act_non_blocking:
            wait_read(self.uv_fd, self.gettimeout(), socket.timeout("timed out"))

        return self.uv_fd.recvfrom(*args)

    def recvfrom_into (self, *args):
        if not self.uv_fd:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        if not self.act_non_blocking:
            wait_read(self.uv_fd, self.gettimeout(), socket.timeout("timed out"))

        return self.uv_fd.recvfrom_into(*args)

    def recv_into (self, buf, nbytes = None, flags = None):
        if not self.uv_fd:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        if not nbytes:
            nbytes = len(buf)

        if not flags:
            flags = 0

        if not self.act_non_blocking:
            wait_read(self.uv_fd, self.gettimeout(), socket.timeout("timed out"))

        return self.uv_fd.recv_into(buf, nbytes = nbytes, flags = flags)


    def recv (self, buflen, flags = 0):
        """
        Receive data from the socket. The return value is a string representing the data received.
        The maximum amount of data to be received at once is specified by bufsize. See the Unix
        manual page recv(2) for the meaning of the optional argument flags; it defaults to zero.

        :param buflen: the maximum length we want from to receive from the socket
        :param flags:
        :return:
        """
        if self.act_non_blocking:
            return self.uv_fd.recv(buflen, flags)
        elif self.uv_handle:
            tot_read = len(self.uv_recv_string)
            if tot_read < buflen:

                did_read = Event()

                def read_callback (handle, data, error):
                    try:
                        self.uv_handle.stop_read()
                        if error:
                            if pyuv.errno.errorcode[error] == 'UV_EOF':
                                did_read.send(GreenSocket.EOF)
                            else:
                                did_read.send_exception(
                                    last_socket_error(error, msg = 'read error'))
                        elif data is None or len(data) == 0:
                            did_read.send(GreenSocket.EOF)
                        else:
                            ## append the data to the buffer and, maybe, stop reading...
                            self.uv_recv_string += data
                            did_read.send()

                    except Exception, e:
                        did_read.send_exception(e)

                ## TODO: we cannot use start_read for UDP!!

                if isinstance(self.uv_handle, pyuv.TCP):
                    self.uv_handle.start_read(read_callback)
                    did_read.wait(self.gettimeout(), socket.timeout("timed out"))
                elif isinstance(self.uv_handle, pyuv.UDP):
                    raise NotImplementedError('not implemented yet for UDP sockets')

            ## get the data we want from the read buffer, and keep the rest
            res, self.uv_recv_string = self.uv_recv_string[:buflen], self.uv_recv_string[buflen:]
            return res
        else:
            fd = self.uv_fd
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


    def send (self, data, flags = 0):
        """
        Send data to the socket. The socket must be connected to a remote socket. The optional
        flags argument has the same meaning as for recv() above. Returns the number of bytes sent.
        Applications are responsible for checking that all data has been sent; if only some of the
        data was transmitted, the application needs to attempt delivery of the remaining data.
        :param data: the data to send
        :param flags: modifier flags
        :return: the amount of data written to the socket
        """
        if self.act_non_blocking:
            return self.uv_fd.send(data, flags)
        elif self.uv_handle:
            did_write = Event()
            write_len = len(data)

            def write_callback (handle, error):
                try:
                    if error:
                        did_write.send_exception(last_socket_error(error, msg = 'write error'))
                    else:
                        did_write.send(write_len)
                except Exception, e:
                    did_write.send_exception(e)

            self.uv_handle.write(data, write_callback)
            return did_write.wait(self.gettimeout(), socket.timeout(errno.ETIME, "timed out"))
        else:
            fd = self.uv_fd
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

                wait_write(self.uv_fd, self.gettimeout(), socket.timeout("timed out"))

            return total_sent

    def sendall (self, data, flags = 0):
        """
        Send data to the socket. The socket must be connected to a remote socket. The optional
        flags argument has the same meaning as for recv() above. Unlike send(), this method
        continues to send data from string until either all data has been sent or an error occurs.
        None is returned on success. On error, an exception is raised, and there is no way to
        determine how much data, if any, was successfully sent.
        :param data:
        :param flags:
        :return: None is returned on success
        """
        tail = self.send(data, flags)
        len_data = len(data)
        while tail < len_data:
            tail += self.send(data[tail:], flags)

    def sendto (self, *args):
        """
        Send data to the socket. The socket should not be connected to a remote socket, since the
        destination socket is specified by address. The optional flags argument has the same meaning
        as for recv() above. Return the number of bytes sent.
        :param args:
        :return:
        """
        ## TODO
        wait_write(self.uv_fd)
        return self.uv_fd.sendto(*args)

    def getsockname (self):
        if self.uv_handle:
            try:
                return self.uv_handle.getsockname()
            except pyuv.error.TCPError, e:
                raise socket.error(*last_socket_error(e.args[0]))
        else:
            return self.uv_fd.getsockname()

    def getpeername (self):
        if self.uv_handle:
            try:
                return self.uv_handle.getpeername()
            except pyuv.error.TCPError, e:
                raise socket.error(*last_socket_error(e.args[0]))
        else:
            return self.uv_fd.getpeername()

    def setsockopt (self, *args, **kwargs):
        return self.uv_fd.setsockopt(*args, **kwargs)

    def shutdown (self, *args):
        """
        Shut down one or both halves of the connection. If how is SHUT_RD, further receives are
        disallowed. If how is SHUT_WR, further sends are disallowed. If how is SHUT_RDWR, further
        sends and receives are disallowed. Depending on the platform, shutting down one half of
        the connection can also close the opposite half (e.g. on Mac OS X, shutdown(SHUT_WR) does
        not allow further reads on the other end of the connection).
        :param args:
        :return:
        """
        if self.uv_handle:
            shudown_event = Event()

            def _shutdown_callback (tcp_handle, error):
                shudown_event.send()

            self.uv_handle.shutdown(_shutdown_callback)
            shudown_event.wait()
        else:
            self.uv_fd.shutdown(*args)

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

