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

from errno import EAGAIN

from evy.hubs import wait_write

__sendfile = __import__('sendfile')

__patched__ = ['sendfile']

## TODO: replace this sendfile for a call to the uv sendfile

def sendfile(out_fd, in_fd, offset, count):
    total_sent = 0
    while total_sent < count:
        try:
            _offset, sent = __sendfile.sendfile(out_fd, in_fd, offset + total_sent, count - total_sent)
            #print '%s: sent %s [%d%%]' % (out_fd, sent, 100*total_sent/count)
            total_sent += sent
        except OSError, ex:
            if ex[0] == EAGAIN:
                wait_write(out_fd)
            else:
                raise
    return offset + total_sent, total_sent

