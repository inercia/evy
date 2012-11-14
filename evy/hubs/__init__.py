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

from evy.support import greenlets as greenlet
from evy import patcher

__all__ = ["use_hub",
           "get_hub",
           "get_default_hub",
           "trampoline"]

threading = patcher.original('threading')
_threadlocal = threading.local()




def get_default_hub ():
    """
    Select the default hub implementation based on what multiplexing
    libraries are installed.  The order that the hubs are tried is:
    
    * uv

    .. include:: ../../doc/common.txt
    .. note :: |internal|
    """
    import evy.hubs.hub
    return evy.hubs.hub


def use_hub (mod = None):
    """
    Use the module *mod*, containing a class called Hub, as the
    event hub. Usually not required; the default hub is usually fine.  
    
    Calling this function has no effect, as we always use the uv hub.
    """
    if hasattr(_threadlocal, 'hub'):
        del _threadlocal.hub

    _threadlocal.Hub = get_default_hub().Hub


def get_hub ():
    """
    Get the current event hub singleton object.
    
    .. note :: |internal|
    """
    try:
        hub = _threadlocal.hub
    except AttributeError:
        try:
            _threadlocal.Hub
        except AttributeError:
            use_hub()

        hub = _threadlocal.hub = _threadlocal.Hub()

    return hub


from evy import timeout


def trampoline (fd, read = None, write = None, timeout = None,
                timeout_exc = timeout.Timeout):
    """
    Suspend the current coroutine until the given socket object or file descriptor is ready to *read*,
    ready to *write*, or the specified *timeout* elapses, depending on arguments specified.

    To wait for *fd* to be ready to read, pass *read* ``=True``; ready to write, pass *write* ``=True``.
    To specify a timeout, pass the *timeout* argument in seconds.

    If the specified *timeout* elapses before the socket is ready to read or write, *timeout_exc*
    will be raised instead of ``trampoline()`` returning normally.
    
    .. note :: |internal|
    """
    t = None
    hub = get_hub()
    current = greenlet.getcurrent()

    assert hub.greenlet is not current, 'do not call blocking functions from the mainloop'
    assert not (read and write), 'not allowed to trampoline for reading and writing'

    try:
        fileno = fd.fileno()
    except AttributeError:
        fileno = fd

    if timeout is not None:
        t = hub.schedule_call_global(timeout, current.throw, timeout_exc)
    try:
        if read:
            listener = hub.add(hub.READ, fileno, current.switch)
        elif write:
            listener = hub.add(hub.WRITE, fileno, current.switch)

        try:
            return hub.switch()
        finally:
            hub.remove(listener)
    finally:
        if t is not None:
            t.cancel()

