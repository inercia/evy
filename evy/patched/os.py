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


os_orig = __import__("os")
import errno

socket = __import__("socket")

from evy.support import get_errno
from evy.io.pipes import GreenPipe

from evy import greenthread
from evy import hubs
from evy.patcher import slurp_properties

__all__ = os_orig.__all__
__patched__ = ['fdopen', 'read', 'write', 'wait', 'waitpid']

slurp_properties(os_orig, globals(),
                 ignore = __patched__, srckeys = dir(os_orig))

def fdopen (fd, *args, **kw):
    """
    fdopen(fd [, mode='r' [, bufsize]]) -> file_object
    
    Return an open file object connected to a file descriptor."""
    if not isinstance(fd, int):
        raise TypeError('fd should be int, not %r' % fd)
    try:
        return GreenPipe(fd, *args, **kw)
    except IOError, e:
        raise OSError(*e.args)

__original_read__ = os_orig.read

def read (fd, n):
    """
    read(fd, buffersize) -> string
    
    Read a file descriptor."""
    while True:
        try:
            return __original_read__(fd, n)
        except (OSError, IOError), e:
            if get_errno(e) != errno.EAGAIN:
                raise
        except socket.error, e:
            if get_errno(e) == errno.EPIPE:
                return ''
            raise
        hubs.trampoline(fd, read = True)

__original_write__ = os_orig.write

def write (fd, st):
    """
    write(fd, string) -> byteswritten
    
    Write a string to a file descriptor.
    """
    while True:
        try:
            return __original_write__(fd, st)
        except (OSError, IOError), e:
            if get_errno(e) != errno.EAGAIN:
                raise
        except socket.error, e:
            if get_errno(e) != errno.EPIPE:
                raise
        hubs.trampoline(fd, write = True)


def wait ():
    """
    wait() -> (pid, status)
    
    Wait for completion of a child process.
    """
    return waitpid(0, 0)

__original_waitpid__ = os_orig.waitpid

def waitpid (pid, options):
    """
    waitpid(...)
    waitpid(pid, options) -> (pid, status)
    
    Wait for completion of a given child process.
    """
    if options & os_orig.WNOHANG != 0:
        return __original_waitpid__(pid, options)
    else:
        new_options = options | os_orig.WNOHANG
        while True:
            rpid, status = __original_waitpid__(pid, new_options)
            if rpid and status >= 0:
                return rpid, status
            greenthread.sleep(0.01)

# TODO: open
