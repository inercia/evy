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

import socket

from evy.uv.interface import libuv, ffi, C
from evy.uv.errors import uv_last_exception


MAX_HOSTNAME_LEN = 128

def malloc(size, destructor = None):
    """
    Return a new cdata object that points to some memory that, when this new cdata object is
    garbage-collected, destructor(old_cdata_object) will be called.
    :param size: th desired size for the allocated memory
    :param destructor: a destructor function that will be invoked when this memory is garbage collected. it will accept the cdata pointer as parameter
    :return:
    """
    assert callable(destructor)

    def _destructor(pointer):
        if destructor:
            destructor(pointer)
        C.free(pointer)

    ptr = ffi.gc(C.malloc(size), _destructor)


def sockaddr_to_tuple(family, addr):
    """
    Obtains the address and port that corresponds to a sockaddr
    :param addr: a struct sockaddr, as a cdata
    :return: a tuple, with address and port
    """

    c_name = ffi.new('char[]', MAX_HOSTNAME_LEN)
    if family == socket.AF_INET:
        addr_in = ffi.cast('struct sockaddr_in*', addr)
        c_port = addr_in[0].sin_port
        res = libuv.uv_ip4_name(addr_in, c_name, MAX_HOSTNAME_LEN)
        if res != 0: uv_last_exception()

    elif family == socket.AF_INET6:
        addr_in = ffi.cast('struct sockaddr_in6*', addr)
        c_port = addr_in[0].sin6_port
        res = libuv.uv_ip6_name(addr_in, c_name, MAX_HOSTNAME_LEN)
        if res != 0: uv_last_exception()

    return ffi.string(c_name), socket.ntohs(int(c_port))



