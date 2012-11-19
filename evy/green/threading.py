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
Implements the standard threading module, using greenthreads.
"""


from evy import patcher
from evy.green import thread
from evy.green import time
from evy.support import greenlets as greenlet

__patched__ = ['_start_new_thread', '_allocate_lock', '_get_ident', '_sleep',
               'local', 'stack_size', 'Lock', 'currentThread',
               'current_thread', '_after_fork', '_shutdown']

__orig_threading = patcher.original('threading')
__threadlocal = __orig_threading.local()

patcher.inject('threading',
               globals(),
    ('thread', thread),
    ('time', time))

del patcher

_count = 1

class _GreenThread(object):
    """Wrapper for GreenThread objects to provide Thread-like attributes
    and methods"""

    def __init__ (self, g):
        global _count
        self._g = g
        self._name = 'GreenThread-%d' % _count
        _count += 1

    def __repr__ (self):
        return '<_GreenThread(%s, %r)>' % (self._name, self._g)

    def join (self, timeout = None):
        return self._g.wait()

    def getName (self):
        return self._name

    get_name = getName

    def setName (self, name):
        self._name = str(name)

    set_name = setName

    name = property(getName, setName)

    ident = property(lambda self: id(self._g))

    def isAlive (self):
        return True

    is_alive = isAlive

    daemon = property(lambda self: True)

    def isDaemon (self):
        return self.daemon

    is_daemon = isDaemon


__threading = None

def _fixup_thread (t):
    # Some third-party packages (lockfile) will try to patch the
    # threading.Thread class with a get_name attribute if it doesn't
    # exist. Since we might return Thread objects from the original
    # threading package that won't get patched, let's make sure each
    # individual object gets patched too our patched threading.Thread
    # class has been patched. This is why monkey patching can be bad...
    global __threading
    if not __threading:
        __threading = __import__('threading')

    if (hasattr(__threading.Thread, 'get_name') and
        not hasattr(t, 'get_name')):
        t.get_name = t.getName
    return t


def current_thread ():
    g = greenlet.getcurrent()
    if not g:
        # Not currently in a greenthread, fall back to standard function
        return _fixup_thread(__orig_threading.current_thread())

    try:
        active = __threadlocal.active
    except AttributeError:
        active = __threadlocal.active = {}

    try:
        t = active[id(g)]
    except KeyError:
        # Add green thread to active if we can clean it up on exit
        def cleanup (g):
            del active[id(g)]

        try:
            g.link(cleanup)
        except AttributeError:
            # Not a GreenThread type, so there's no way to hook into
            # the green thread exiting. Fall back to the standard
            # function then.
            t = _fixup_thread(__orig_threading.currentThread())
        else:
            t = active[id(g)] = _GreenThread(g)

    return t

currentThread = current_thread
