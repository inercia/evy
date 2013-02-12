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
import errno
import socket

from socket import socket as _original_socket



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
    #'UV_ENOTSUP' : errno.ENOTSUP,
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


def get_errno (exc):
    """
    Get the error code out of socket.error objects.
    socket.error in <2.5 does not have errno attribute
    socket.error in 3.x does not allow indexing access
    e.args[0] works for all.

    There are cases when args[0] is not errno.
    i.e. http://bugs.python.org/issue6471
    Maybe there are cases when errno is set, but it is not the first argument?
    """

    try:
        if exc.errno is not None: return exc.errno
    except AttributeError:
        pass
    try:
        return exc.args[0]
    except IndexError:
        return None

def last_file_error(code, msg = None):
    """
    Utility function for getting the last exception as a IOerror
    """
    if msg: msg += ': %s' % (pyuv.errno.strerror(code))
    else:   msg = '%s' % (pyuv.errno.strerror(code))

    try:                errno_code = _UV_ERR_TO_ERRNO_MAP[pyuv.errno.errorcode[code]]
    except KeyError:    errno_code = code

    return IOError(errno_code, msg)



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

