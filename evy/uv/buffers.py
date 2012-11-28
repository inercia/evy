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


from evy.uv.interface import ffi




class uv_buffer(object):
    """
    Buffers for using with UV

    In order to work with UV, we must keep references not only to the uv_buf_t, but also to the
    memory allocated for the base. This class keeps both things together: the `uv_buffer_t` and the
    `char*` that is the base...
    """

    __slots__ = ['_len', '_base', '_buffer']


    def __init__(self, length = None, data = None):
        if length:
            self._len = length
        else:
            assert data is not None
            self._len = len(data)

        if data:
            self._base = ffi.new("char[]", data)
        else:
            self._base = ffi.new("char[%d]" % length)

        buffer_def = {
            'base': self._base,
            'len': self._len,
            }
        self._buffer = ffi.new('uv_buf_t*', buffer_def)

    @property
    def ptr(self):
        return self._buffer

    @property
    def data(self):
        """
        Return the data as a string
        :return:
        """
        return self.__str__()

    @property
    def length(self):
        return self._buffer[0].len

    def as_struct(self):
        return self._buffer[0]

    def slice(self, datalen):
        return ffi.string(self._buffer[0].base, datalen)

    def __len__(self):
        return self.length

    def __call__(self, *args, **kwargs):
        return self.ptr

    def __getitem__(self, key):
        return self.as_struct()             ## we always return the same: the struct

    def __str__(self):
        return ffi.string(self._buffer[0].base, self.length)

    def __repr__(self):
        return '<uv_buffer with %s [%d bytes]>' % (repr(self._base), self._len)

    def __eq__(self, other):
        return (self._base == other._base) and (self._len == other._len)


