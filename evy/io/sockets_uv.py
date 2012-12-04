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

        # buffer allocations
        self.uv_recv_string = ''


    def _uv_read_callback(self, handle, data, error):
        """
        The callback invoked when we read something from the socket
        """
        try:
            if error:
                if pyuv.errno.errorcode[error] == 'UV_EOF':
                    self.did_read.send(BaseSocket.EOF)
                else:
                    self.did_read.send_exception(last_socket_error(error, msg = 'read error'))
            elif data is None or len(data) == 0:
                self.did_read.send(BaseSocket.EOF)
            else:
                ## append the data to the buffer and, maybe, stop reading...
                self.uv_recv_string += data

                tot_len = len(self.uv_recv_string)
                if  tot_len >= self.uv_recv_string_limit:
                    self.did_read.send(tot_len)

        except Exception, e:
            self.did_read.send_exception(e)


    def _uv_write_callback(self, handle, error):
        """
        The callback invoked when we are done writting to the socket
        """
        try:
            assert hasattr(self, 'did_write')
            assert hasattr(self, 'uv_write_len')

            ## free the write request and the temporal buffer used for sending
            l = self.uv_write_len
            del self.uv_write_len

            if error:   self.did_write.send_exception(last_socket_error(error, msg = 'write error'))
            else:       self.did_write.send(l)

        except Exception, e:
            self.did_write.send_exception(e)

    def _uv_accept_callback(self, handle, error):
        """
        The callback invoked when we receive a connection request
        :param stream: the uv_stream handler for the server
        """
        if error:
            self.did_accept.send_exception(last_socket_error(error, msg = 'accept error'))

        try:
            ## create the handle for the newly accepted connection
            new_handle = pyuv.TCP(self.uv_hub.uv_loop)
            res = self.uv_handle.accept(new_handle)
            new_sock = TcpSocket(uv_hub = self.uv_hub, uv_handle = new_handle)
            new_sock_addr, _ = new_sock.getpeername()
            self.did_accept.send((new_sock, new_sock_addr))

        except Exception, e:
            self.did_accept.send_exception(e)


    def _uv_connect_callback(self, handle, error):
        """
        The callback invoked when we are finally connected to the remote peer
        """
        try:
            if error:  self.did_connect.send_exception(last_socket_error(error, msg = 'connect error'))
            else:      self.did_connect.send(0)

        except Exception, e:
            self.did_connect.send_exception(e)





    def bind(self, address):
        """
        Binds to a particular address and port

        :param address: the address
        """
        assert self.uv_handle
        res = self.uv_handle.bind(resolve_address(address))


    def listen(self, backlog):
        """
        Listen for a new connection

        :param backlog: the backlog
        """
        self.backlog = backlog
        assert self.backlog is not None
        if not self.uv_handle:
            raise socket.error(errno.EBADFD, 'invalid file descriptor')

        try:
            self.uv_handle.listen(self._uv_accept_callback)
        except pyuv.error.TCPError, e:
            print dir(e)
            raise socket.error(last_socket_error(0, msg = 'listen error'))


    def accept (self):
        """
        Accept a new connection when we are listening
        :return:
        """
        return self.did_accept.wait()        ## this could raise an exception...

    def connect(self, address):
        """
        Connects to a remote address
        :param address: the remote address, as a IP and port tuple
        """
        self.uv_connect_req_addr = address
        with Timeout(self.gettimeout(), socket.timeout("timed out")):
            try:
                self.uv_handle.connect(resolve_address(address), self._uv_connect_callback)
                self.did_connect.wait()
            finally:
                self.did_connect = Event()

    def connect_ex (self, address):
        """
        Connects to a remote address not raising exceptions
        :param address: the remote address, as a IP and port tuple
        :return: 0 if successful, or an error code otherwise
        """
        try:
            self.uv_handle.connect(address, self._uv_connect_callback)
            self.did_connect.wait()
            return 0
        except Timeout:
            return errno.ETIME
        except Exception, e:
            return e.code


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
        if not nbytes:
            nbytes = len(buf)

        if nbytes == 0:
            raise ValueError('invalid read length')

        temp_buf = self.recv(nbytes)
        v = len(temp_buf)
        buf[:v] = temp_buf
        return v

    def recv (self, buflen, flags = 0):
        """
        Receive data from the socket. The return value is a string representing the data received.
        The maximum amount of data to be received at once is specified by bufsize. See the Unix
        manual page recv(2) for the meaning of the optional argument flags; it defaults to zero.

        :param buflen: the maximum length we want from to receive from the socket
        :param flags:
        :return:
        """
        tot_read = 0
        with Timeout(self.gettimeout(), socket.timeout("timed out")):
            try:
                self.uv_recv_string_limit = buflen
                res = self.uv_handle.start_read(self._uv_read_callback)
                tot_read = self.did_read.wait()

                if tot_read == BaseSocket.EOF or tot_read >= self.uv_recv_string_limit:
                    self.uv_handle.stop_read()

                ## get the data we want from the read buffer, and keep the rest
                res = self.uv_recv_string[:buflen]
                self.uv_recv_string = self.uv_recv_string[buflen:]
            finally:
                self.did_read = Event()

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
        self.did_write = Event()
        with Timeout(self.gettimeout(), socket.timeout("timed out")):
            self.uv_write_len = len(data)
            self.uv_handle.write(data, self._uv_write_callback)
            write_result = self.did_write.wait()
            ## TODO: check if the connection has been broken, etc...

        del self.did_write

        return write_result

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
