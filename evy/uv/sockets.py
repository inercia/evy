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

from evy.uv.interface import libuv, ffi, cast_to_handle
from evy.uv.errors import uv_last_error, uv_last_exception
from evy.uv.utils import sockaddr_to_tuple

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


####################################################################################################

class BaseSocket(object):

    UV_HANDLE_TYPE = 'uv_stream_t*'

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None, **kwargs):
        """
        Initialize the socket
        """
        self.family = family
        self.type = type
        self.proto = proto

        self.uv_fileno = None
        self.uv_handle = None

        if 'uv_handle' in kwargs:
            self.uv_handle = ffi.cast(self.UV_HANDLE_TYPE, kwargs['uv_handle'])
        elif _sock:
            self.fd = _sock
            self.uv_fileno = self.fd.fileno()

        # import timeout from other socket, if it was there
        try:
            self._timeout = self.fd.gettimeout() or socket.getdefaulttimeout()
        except AttributeError:
            self._timeout = socket.getdefaulttimeout()

        # when client calls setblocking(0) or settimeout(0) the socket must act non-blocking
        self.act_non_blocking = False


    def close(self):
        def closed_callback(handle):
            self.uv_handle = None
            self.uv_fileno = None

        if self.uv_handle:
            uv_handle = cast_to_handle(self.uv_handle)

            ## we must remove all pollers on this socket
            get_hub().remove_descriptor(self.uv_fileno, skip_callbacks = True)

            if not libuv.uv_is_closing(uv_handle):
                _closed_callback = ffi.callback('void(*)(uv_handle_t*)', closed_callback)
                libuv.uv_close(uv_handle, _closed_callback)


    @property
    def _sock (self):
        return self

    def dup (self, *args, **kw):
        sock = self.fd.dup(*args, **kw)
        #set_nonblocking(sock)
        newsock = type(self)(sock)
        newsock.settimeout(self.gettimeout())
        return newsock

    def makefile (self, *args, **kw):
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

    ##
    ## connect request
    ##

    def _get_uv_connect_req(self):
        if not hasattr(self, '_uv_connect_req'):
            self._uv_connect_req = ffi.new('uv_connect_t*')
        return self._uv_connect_req

    def _del_uv_connect_req(self):
        del self._uv_connect_req

    uv_connect_req = property(_get_uv_connect_req, None, _del_uv_connect_req)

    ##
    ## write request
    ##

    def _get_uv_write_req(self):
        if not hasattr(self, '_uv_write_req'):
            self._uv_write_req = ffi.new('uv_write_t*')
        return self._uv_write_req

    def _del_uv_write_req(self):
        del self._uv_write_req

    uv_write_req = property(_get_uv_write_req, None, _del_uv_write_req)

    @property
    def closing(self):
        """
        Used to determine whether a socket is closing or closed.

        It is only valid between the initialization of the handle and the arrival of the close
        callback, and cannot be used to validate the handle.

        :return: True if the socket is closed or being closed
        """
        if self.uv_handle:  return libuv.uv_is_closing(cast_to_handle(self.uv_handle))
        else:               return True


    def uv_ip_addr(self, address):
        """
        Get an IP address in libuv-compatible format
        """
        assert len(address) == 2
        addr, port = address
        if len(addr) == 0: addr = '0.0.0.0'

        if self.family == socket.AF_INET:       return libuv.uv_ip4_addr(addr, port)
        elif self.family == socket.AF_INET6:    return libuv.uv_ip6_addr(addr, port)
        else:                                   raise RuntimeError()

    @property
    def uv_struct_sockaddr_in(self):
        if self.family == socket.AF_INET:       return 'struct sockaddr_in'
        elif self.family == socket.AF_INET6:    return 'struct sockaddr_in6'
        else:                                   raise RuntimeError()

    @property
    def uv_stream(self):
        """
        The handle as a uv_stream
        """
        assert self.uv_handle
        return ffi.cast('uv_stream_t*', self.uv_handle)

####################################################################################################

class TcpSocket(BaseSocket):
    """
    libUV version of a Tcp (V4 or V6) socket
    """

    UV_HANDLE_TYPE = 'uv_tcp_t*'

    def __init__ (self, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, _sock = None, **kwargs):
        """
        Initialize the socket
        """
        super(TcpSocket, self).__init__(family, type, proto, _sock, **kwargs)

        hub = get_hub()
        assert hub.ptr is not None

        if not self.uv_handle:
            self.uv_handle = ffi.new(self.UV_HANDLE_TYPE)
            libuv.uv_tcp_init(hub.ptr, self.uv_handle)

            if self.uv_fileno:
                libuv.uv_tcp_open(self.uv_handle, self.uv_fileno)

            assert self.uv_handle is not None

        # some events
        self.did_accept = Event()
        self.did_connect = Event()
        self.did_read = Event()
        self.did_write = Event()

        # buffer allocation and co.
        self.uv_recv_buffer = None

        def _uv_alloc_callback(handle, suggested_size):
            """
            The callback invoked by libuv when it needs a new buffer
            :param handle:
            :param suggested_size:
            :return:
            """
            self.uv_recv_buffer =  ffi.new("char[]", suggested_size)
            return libuv.uv_buf_init(self.uv_recv_buffer, suggested_size)

        self.uv_alloc_callback = ffi.callback("void(*)(uv_handle_t*, size_t)", _uv_alloc_callback)


        def _uv_listen_callback(stream, status):
            """
            The callback invoked when we receive a connection request
            :param stream: the uv_stream handler for the server
            """

            ## create the handle for the newly accepted connection
            new_handle = ffi.new('uv_tcp_t*')
            libuv.uv_tcp_init(hub.ptr, new_handle)

            res = libuv.uv_accept(self.uv_stream, ffi.cast('uv_stream_t*', new_handle))
            if res != 0:
                self.did_accept.send_exception(socket.error(*uv_last_error()))
            else:
                new_sock = TcpSocket(uv_handle = new_handle)
                new_sock_addr, new_sock_port = new_sock.getpeername()
                self.did_accept.send((new_sock, new_sock_addr))

        self.uv_listen_callback = ffi.callback(" void (*)(uv_stream_t* server, int status)", _uv_listen_callback)


        def _uv_connect_callback(req, status):
            """
            The callback invoked when we are finally connected to the remote peer
            """
            del self.uv_connect_req

            if status < 0:  self.did_connect.send_exception(socket.error(*uv_last_error()))
            else:           self.did_connect.send()

        self.uv_connect_callback = ffi.callback("void(*)(uv_connect_t*, int)", _uv_connect_callback)

        def _uv_read_callback(stream, nread, buf):
            """
            The callback invoked when we read something from the socket
            """
            ## TODO: append the data to the reception buffer
            self.did_read.send(nread)

        self.uv_read_callback = ffi.callback("void(*)(uv_stream_t*, ssize_t, uv_buf_t)", _uv_read_callback)

        def _uv_write_callback(req, status):
            res = uv_last_error() if status < 0 else 0
            del self.uv_write_req
            self.did_write.send(res)

        self.uv_write_callback = ffi.callback("void(*)(uv_write_t*, int)", _uv_write_callback)




    def bind(self, address):
        """
        Binds to a particular address and port

        :param address: the address
        """
        assert self.uv_handle
        assert ffi.typeof(self.uv_handle) is ffi.typeof("uv_tcp_t*")

        addr = self.uv_ip_addr(address)

        if self.family == socket.AF_INET:       res = libuv.uv_tcp_bind(self.uv_handle, addr)
        elif self.family == socket.AF_INET6:    res = libuv.uv_tcp_bind6(self.uv_handle, addr)
        else:                                   raise RuntimeError('unknown socket family')

        assert (res != 0) or (address[1] == 0 and self.getsockname()[1] != 0) or (self.getsockname()[1] == address[1])

        if res != 0:    uv_last_exception()
        else:           return 0

    def listen(self, backlog):
        """
        Listen for a new connection

        :param backlog: the backlog
        """
        assert ffi.typeof(self.uv_handle) is ffi.typeof("uv_tcp_t*")
        self.backlog = backlog


    def accept (self):
        """
        Accept a new connection when we are listening
        :return:
        """
        res = libuv.uv_listen(self.uv_stream, self.backlog, self.uv_listen_callback)
        if res != 0:    raise socket.error('listen error: %d' % uv_last_error())
        else:           return self.did_accept.wait()        ## this could raise an exception...


    def _connect(self, address):
        _addr = self.uv_ip_addr(address)
        if self.family == socket.AF_INET:   connect_fun = libuv.uv_tcp_connect
        elif self.family == socket.AF_INET: connect_fun = libuv.uv_tcp_connect6

        err = connect_fun(self.uv_connect_req, self.uv_handle, _addr, self.uv_connect_callback)
        if err != 0:    uv_last_exception()
        else:           return self.did_connect.wait()    ## this wait() can raise an exception...

    def connect(self, address):
        """
        Connects to a remote address
        :param address: the remote address, as a IP and port tuple
        """
        with Timeout(self.gettimeout(), socket.timeout("timed out")):
            return self._connect(address)

    def connect_ex (self, address):
        """
        Connects to a remote address not raising exceptions
        :param address: the remote address, as a IP and port tuple
        :return: 0 if successful, or an error code otherwise
        """
        try:
            res = self.connect(address)
        except Timeout:
            return errno.ETIME
        except:
            return uv_last_error()[0]

        return res


    def recv (self, buflen, flags = 0):
        """
        Receive from the socket
        :param buflen: the maximum length we want from to receive from the socket
        :param flags:
        :return:
        """
        with Timeout(self.gettimeout(), socket.timeout("timed out")):
            while len(self.uv_recv_buffer) < buflen:
                libuv.uv_read_start(self.uv_stream, self.uv_alloc_callback, self.uv_read_callback)
                read_result = self.did_read.wait()
                ## TODO: check if the connection has been broken, etc...

        return self.uv_recv_buffer


    def recvfrom (self, *args):
        ## TODO
        raise RuntimeError('not implemented')

    def recvfrom_into (self, *args):
        ## TODO
        raise RuntimeError('not implemented')

    def recv_into (self, *args):
        ## TODO
        raise RuntimeError('not implemented')

    def send (self, data, flags = 0):
        buf = libuv.uv_buf_init(data, len(data))

        with Timeout(self.gettimeout(), socket.timeout("timed out")):
            res = libuv.uv_write(self.uv_write_req, self.uv_handle, buf, 1, self.uv_write_callback)
            write_result = self.did_write.wait()
            ## TODO: check if the connection has been broken, etc...

        return write_result

    def sendall (self, data, flags = 0):
        tail = self.send(data, flags)
        len_data = len(data)
        while tail < len_data:
            tail += self.send(data[tail:], flags)

    def sendto (self, *args):
        ## TODO
        raise RuntimeError('not implemented')

    def getsockname(self):
        addr = ffi.new(self.uv_struct_sockaddr_in + '*')
        addrlen = ffi.new('int*')
        addrlen[0] = ffi.sizeof(self.uv_struct_sockaddr_in)
        res = libuv.uv_tcp_getsockname(self.uv_handle, ffi.cast('struct sockaddr*', addr), addrlen)
        if res != 0:    uv_last_exception()
        else:           return sockaddr_to_tuple(self.family, addr)

    def getpeername(self):
        addr = ffi.new(self.uv_struct_sockaddr_in + '*')
        addrlen = ffi.new('int*')
        addrlen[0] = ffi.sizeof(self.uv_struct_sockaddr_in)
        res = libuv.uv_tcp_getpeername(self.uv_handle, ffi.cast('struct sockaddr*', addr), addrlen)
        if res != 0:    uv_last_exception()
        else:           return sockaddr_to_tuple(self.family, addr)

    def setsockopt(self, *args, **kwargs):
        pass
