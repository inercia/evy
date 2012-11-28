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

import os
import errno
import socket


from evy.hubs import get_hub

from evy.uv.interface import libuv


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

def uv_error_to_errno(code, not_found = None):
    """
    Obtain the mapping between uv errors and errno
    :param code: the uv code
    :param not_found: the result if there is not valid mapping
    :return: an errno
    """
    try:
        return _UV_ERR_TO_ERRNO_MAP[code]
    except KeyError:
        return not_found

def uv_last_error_str():
    hub = get_hub()
    return str(libuv.uv_last_error(hub.ptr).code)

def uv_last_error():
    """
    Get the last libuv error that happened
    :return: a tuple with the errno equivalent and the string representation
    """
    _errno = uv_error_to_errno(uv_last_error_str, not_found = 0)

    if _errno is 0: return 0, 'none'
    else:           return _errno, os.strerror(_errno)

def uv_last_exception(exception = socket.error):
    """
    Raise the exception for the last error
    """
    raise exception(*uv_last_error())
