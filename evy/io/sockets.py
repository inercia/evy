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

import pyuv

from evy.support import get_errno

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

#: the mapping between libuv errors and errno
_UV_ERR_TO_ERRNO_MAP = {
    'UV_EACCES' : errno.EACCES ,
    'UV_EAGAIN' : errno.EAGAIN,
    'UV_EADDRINUSE' : errno.EADDRINUSE ,
    'UV_EADDRNOTAVAIL' : errno.EADDRNOTAVAIL,
    'UV_EAFNOSUPPORT' : errno.EAFNOSUPPORT,
    'UV_EALREADY' : errno.EALREADY,
    'UV_EBADF' : errno.EBADF,
    'UV_EBUSY' : errno.EBUSY,
    'UV_ECONNABORTED' : errno.ECONNABORTED,
    'UV_ECONNREFUSED' : errno.ECONNREFUSED ,
    'UV_ECONNRESET' : errno.ECONNRESET,
    'UV_EDESTADDRREQ' : errno.EDESTADDRREQ,
    'UV_EFAULT' : errno.EFAULT,
    'UV_EHOSTUNREACH' : errno.EHOSTUNREACH,
    'UV_EINTR' : errno.EINTR,
    'UV_EINVAL' : errno.EINVAL,
    'UV_EISCONN' : errno.EISCONN,
    'UV_EMFILE' : errno.EMFILE,
    'UV_EMSGSIZE' : errno.EMSGSIZE,
    'UV_ENETDOWN' : errno.ENETDOWN,
    'UV_ENETUNREACH' : errno.ENETUNREACH,
    'UV_ENFILE' : errno.ENFILE,
    'UV_ENOBUFS' : errno.ENOBUFS,
    'UV_ENOMEM' : errno.ENOMEM,
    'UV_ENOTDIR' : errno.ENOTDIR,
    'UV_EISDIR' : errno.EISDIR,
    #'UV_ENONET' : errno.ENONET,
    'UV_ENOTCONN' : errno.ENOTCONN,
    'UV_ENOTSOCK' : errno.ENOTSOCK,
    'UV_ENOTSUP' : errno.ENOTSUP,
    'UV_ENOENT' : errno.ENOENT,
    'UV_ENOSYS' : errno.ENOSYS,
    'UV_EPIPE' : errno.EPIPE,
    'UV_EPROTO' : errno.EPROTO,
    'UV_EPROTONOSUPPORT' : errno.EPROTONOSUPPORT,
    'UV_EPROTOTYPE' : errno.EPROTOTYPE,
    'UV_ETIMEDOUT' : errno.ETIMEDOUT,
    'UV_ESHUTDOWN' : errno.ESHUTDOWN,
    'UV_EEXIST' : errno.EEXIST,
    'UV_ESRCH' : errno.ESRCH,
    'UV_ENAMETOOLONG' : errno.ENAMETOOLONG,
    'UV_EPERM' : errno.EPERM,
    'UV_ELOOP' : errno.ELOOP,
    'UV_EXDEV' : errno.EXDEV,
    'UV_ENOTEMPTY' : errno.ENOTEMPTY,
    'UV_ENOSPC' : errno.ENOSPC,
    'UV_EIO' : errno.EIO,
    'UV_EROFS' : errno.EROFS,
    'UV_ENODEV' : errno.ENODEV ,
    'UV_ESPIPE' : errno.ESPIPE ,
}

def last_socket_error(code, msg = None):
    """
    Utility function for getting the last exception as a socket.error
    """
    if msg: msg += ': %s' % (pyuv.errno.strerror(code))
    else:   msg = '%s' % (pyuv.errno.strerror(code))

    try:
        errno_code = _UV_ERR_TO_ERRNO_MAP[pyuv.errno.errorcode[code]]
    except KeyError:
        errno_code = code

    return socket.error(errno_code, msg)



####################################################################################################

class UvBaseSocket(object):

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
    def closed(self):
        """
        Used to determine whether a socket is closed.

        It is only valid between the initialization of the handle and the arrival of the close
        callback, and cannot be used to validate the handle.

        :return: True if the socket is closed or being closed
        """
        try:
            return self.uv_handle.closed
        except AttributeError:
            pass

        return True


####################################################################################################

class UvTcpSocket(UvBaseSocket):
    """
    libUV version of a Tcp (V4 or V6) socket
    """

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None, **kwargs):
        """
        Initialize the socket
        """
        super(UvTcpSocket, self).__init__(family, type, proto, _sock, **kwargs)

        assert hasattr(self, 'uv_handle')
        if not self.uv_handle:
            self.uv_handle = pyuv.TCP(self.uv_hub.uv_loop)

            if self.uv_fileno:
                self.uv_handle.open(self.uv_fileno)

            assert self.uv_handle is not None

        self.uv_recv_string = ''                    # buffer for receiving data...


    def dup (self, *args, **kw):
        new_handle = pyuv.TCP(self.uv_hub.uv_loop)
        return UvTcpSocket(family = socket.AF_INET, type = socket.SOCK_STREAM, uv_hub = self.uv_hub, uv_handle = new_handle)

    def bind(self, address):
        """
        Binds to a particular address and port

        :param address: the address
        """
        assert self.uv_handle
        try:
            self.uv_handle.bind(resolve_address(address))
        except pyuv.error.TCPError, e:
            raise socket.error(last_socket_error(e.args[0], msg = 'listen error'))


    def listen(self, backlog):
        """
        Listen for a new connection

        :param backlog: the backlog
        """
        if not self.uv_handle:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        self.did_listen = Event()
        self.did_accept = Event()

        def listen_callback(handle, error):
            self.did_accept.wait()
            try:
                if error:
                    self.did_listen.send_exception(last_socket_error(error, msg = 'accept error'))
                else:
                    ## create the handle for the newly accepted connection
                    new_handle = pyuv.TCP(self.uv_hub.uv_loop)
                    res = self.uv_handle.accept(new_handle)
                    new_sock = UvTcpSocket(socket.AF_INET, socket.SOCK_STREAM, 0, uv_hub = self.uv_hub, uv_handle = new_handle)
                    new_sock_addr, _ = new_sock.getpeername()
                    self.did_listen.send((new_sock, new_sock_addr))
            except Exception, e:
                self.did_listen.send_exception(e)

        try:
            self.uv_handle.listen(listen_callback)
        except pyuv.error.TCPError, e:
            raise socket.error(last_socket_error(e.args[0], msg = 'listen error'))


    def accept (self):
        """
        Accept a new connection when we are listening
        :return:
        """
        try:
            with Timeout(self.gettimeout(), socket.timeout("timed out")):
                self.did_accept.send()
                return self.did_listen.wait()        ## this could raise an exception...
        except pyuv.error.TCPError, e:
            raise socket.error(last_socket_error(e.args[0], msg = 'accept error'))
        finally:
            self.did_listen = None
            self.did_accept = None

    def connect(self, address):
        """
        Connects to a remote address
        :param address: the remote address, as a IP and port tuple
        """
        if not self.uv_handle:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        with Timeout(self.gettimeout(), socket.timeout((errno.ETIME, "timed out"))):
            try:
                did_connect = Event()

                def connect_callback(tcp_handle, error):
                    try:
                        if error:
                            did_connect.send_exception(last_socket_error(error, msg = 'connect error'))
                        else:
                            did_connect.send(0)
                    except Exception, e:
                        did_connect.send_exception(e)

                self.uv_handle.connect(resolve_address(address), connect_callback)
                did_connect.wait()

            except pyuv.error.TCPError, e:
                raise socket.error(last_socket_error(e.args[0], msg = 'connect error'))

    def connect_ex (self, address):
        """
        Connects to a remote address not raising exceptions
        :param address: the remote address, as a IP and port tuple
        :return: 0 if successful, or an error code otherwise
        """
        if not self.uv_handle:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        try:
            self.connect(address)
            return 0
        except (socket.timeout, Timeout):
            return errno.ETIME
        except pyuv.error.TCPError, e:
            raise socket.error(last_socket_error(e.args[0], msg = 'connect error'))
        except Exception, e:
            code = e.args[0]
            return code


    def recvfrom (self, *args):
        """
        Receive data from the socket. The return value is a pair (string, address) where string is
        a string representing the data received and address is the address of the socket sending
        the data. See the Unix manual page recv(2) for the meaning of the optional argument flags;
        it defaults to zero.
        :param args:
        :return:
        """
        ## TODO
        raise RuntimeError('not implemented')

    def recvfrom_into (self, *args):
        """
        Receive data from the socket, writing it into buffer instead of creating a new string.
        The return value is a pair (nbytes, address) where nbytes is the number of bytes received
        and address is the address of the socket sending the data. See the Unix manual page recv(2)
        for the meaning of the optional argument flags; it defaults to zero.
        :param args:
        :return:
        """
        ## TODO
        raise RuntimeError('not implemented')

    def recv_into (self, buf, nbytes = None, flags = None):
        if not self.uv_handle:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        if not nbytes:
            nbytes = len(buf)

        if nbytes == 0:
            raise ValueError('invalid read length')

        temp_str = self.recv(nbytes)
        buf += temp_str
        return len(temp_str)

    def recv (self, buflen, flags = 0):
        """
        Receive data from the socket. The return value is a string representing the data received.
        The maximum amount of data to be received at once is specified by bufsize. See the Unix
        manual page recv(2) for the meaning of the optional argument flags; it defaults to zero.

        :param buflen: the maximum length we want from to receive from the socket
        :param flags:
        :return:
        """
        if not self.uv_handle:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        tot_read = len(self.uv_recv_string)
        if tot_read < buflen:
            with Timeout(self.gettimeout(), socket.timeout("timed out")):

                did_read = Event()

                def read_callback(handle, data, error):
                    try:
                        if error:
                            if pyuv.errno.errorcode[error] == 'UV_EOF':
                                did_read.send(UvBaseSocket.EOF)
                            else:
                                did_read.send_exception(last_socket_error(error, msg = 'read error'))
                        elif data is None or len(data) == 0:
                            did_read.send(UvBaseSocket.EOF)
                        else:
                            ## append the data to the buffer and, maybe, stop reading...
                            self.uv_recv_string += data
                            did_read.send()

                    except Exception, e:
                        did_read.send_exception(e)

                self.uv_handle.start_read(read_callback)
                did_read.wait()
                self.uv_handle.stop_read()
                tot_read = len(self.uv_recv_string)

            ## get the data we want from the read buffer, and keep the rest
            res, self.uv_recv_string = self.uv_recv_string[:buflen], self.uv_recv_string[buflen:]
            return res

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
        with Timeout(self.gettimeout(), socket.timeout("timed out")):

            did_write = Event()
            write_len = len(data)

            def write_callback(handle, error):
                try:
                    if error:
                        did_write.send_exception(last_socket_error(error, msg = 'write error'))
                    else:
                        did_write.send(write_len)
                except Exception, e:
                    did_write.send_exception(e)

            self.uv_handle.write(data, write_callback)

            ## TODO: check if the connection has been broken, etc...
            return did_write.wait()


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
        raise RuntimeError('not implemented')

    def getsockname(self):
        return self.uv_handle.getsockname()

    def getpeername(self):
        return self.uv_handle.getpeername()

    def setsockopt(self, *args, **kwargs):
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
        if not self.uv_handle:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        shudown_event = Event()
        def _shutdown_callback(tcp_handle, error):
            shudown_event.send()

        self.uv_handle.shutdown(_shutdown_callback)
        shudown_event.wait()



class SimpleSocket(object):

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None):
        """
        Initialize the UV socket

        :param family_or_realsock: a socket descriptor or a socket family
        """
        self.uv_fd = None

        if isinstance(family, (int, long)): fd = _original_socket(family, type, proto, _sock)
        else:                               fd = family

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

    def ioctl(self, *args):
        pass




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

        if isinstance(family, (int, long)):
            if type == socket.SOCK_STREAM:
                self.delegate = UvTcpSocket(family, type, proto, _sock)

        elif isinstance(family, _original_socket):
            _sock = family

            family = _sock .family
            type = _sock.type
            proto = _sock.proto

            if type == socket.SOCK_STREAM:
                self.delegate = UvTcpSocket(family, type, proto, _sock)

        if not self.delegate:
            self.delegate = SimpleSocket(family, type, proto, _sock)

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

