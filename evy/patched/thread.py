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


"""
Implements the standard thread module, using greenthreads.
"""


__thread = __import__('thread')

from evy.support import greenlets as greenlet
from evy.green import threads as greenthread
from evy.semaphore import Semaphore as LockType

__patched__ = ['get_ident', 'start_new_thread', 'start_new', 'allocate_lock',
               'allocate', 'exit', 'interrupt_main', 'stack_size', '_local',
               'LockType', '_count']

error = __thread.error
__threadcount = 0

def _count ():
    return __threadcount


def get_ident (gr = None):
    if gr is None:
        return id(greenlet.getcurrent())
    else:
        return id(gr)


def __thread_body (func, args, kwargs):
    global __threadcount
    __threadcount += 1
    try:
        func(*args, **kwargs)
    finally:
        __threadcount -= 1


def start_new_thread (function, args = (), kwargs = {}):
    g = greenthread.spawn_n(__thread_body, function, args, kwargs)
    return get_ident(g)

start_new = start_new_thread

def allocate_lock (*a):
    return LockType(1)

allocate = allocate_lock

def exit ():
    raise greenlet.GreenletExit

exit_thread = __thread.exit_thread

def interrupt_main ():
    curr = greenlet.getcurrent()
    if curr.parent and not curr.parent.dead:
        curr.parent.throw(KeyboardInterrupt())
    else:
        raise KeyboardInterrupt()

if hasattr(__thread, 'stack_size'):
    __original_stack_size__ = __thread.stack_size

    def stack_size (size = None):
        if size is None:
            return __original_stack_size__()
        if size > __original_stack_size__():
            return __original_stack_size__(size)
        else:
            pass
            # not going to decrease stack_size, because otherwise other greenlets in this thread will suffer

from evy.corolocal import local as _local
