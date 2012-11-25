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
import os
import socket
from socket import socket as _original_socket
import sys

from evy.support import get_errno


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
