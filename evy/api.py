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

import warnings

from evy.support import greenlets as greenlet, BaseException
from evy import hubs
from evy import greenthread
from evy import debug

__all__ = [
    'call_after', 'exc_after', 'getcurrent', 'get_default_hub', 'get_hub',
    'GreenletExit', 'kill', 'sleep', 'spawn', 'spew', 'switch',
    'ssl_listener', 'tcp_listener', 'trampoline',
    'unspew', 'use_hub', 'with_timeout', 'timeout']

warnings.warn("evy.api is deprecated!  Nearly everything in it has moved "
              "to the evy module.", DeprecationWarning, stacklevel = 2)



def switch (coro, result = None, exc = None):
    if exc is not None:
        return coro.throw(exc)
    return coro.switch(result)

Greenlet = greenlet.greenlet

TimeoutError = greenthread.TimeoutError

trampoline = hubs.trampoline

spawn = greenthread.spawn
spawn_n = greenthread.spawn_n
kill = greenthread.kill
call_after = greenthread.call_after
call_after_local = greenthread.call_after_local
call_after_global = greenthread.call_after_global


class _SilentException(BaseException):
    pass


class FakeTimer(object):
    def cancel (self):
        pass


class timeout(object):
    """Raise an exception in the block after timeout.
    
    Example::

     with timeout(10):
         urllib2.open('http://example.com')

    Assuming code block is yielding (i.e. gives up control to the hub),
    an exception provided in *exc* argument will be raised
    (:class:`~evy.api.TimeoutError` if *exc* is omitted)::
    
     try:
         with timeout(10, MySpecialError, error_arg_1):
             urllib2.open('http://example.com')
     except MySpecialError, e:
         print "special error received"


    When *exc* is ``None``, code block is interrupted silently.
    """

    def __init__ (self, seconds, *throw_args):
        self.seconds = seconds
        if seconds is None:
            return
        if not throw_args:
            self.throw_args = (TimeoutError(), )
        elif throw_args == (None, ):
            self.throw_args = (_SilentException(), )
        else:
            self.throw_args = throw_args

    def __enter__ (self):
        if self.seconds is None:
            self.timer = FakeTimer()
        else:
            self.timer = exc_after(self.seconds, *self.throw_args)
        return self.timer

    def __exit__ (self, typ, value, tb):
        self.timer.cancel()
        if typ is _SilentException and value in self.throw_args:
            return True

with_timeout = greenthread.with_timeout

exc_after = greenthread.exc_after

sleep = greenthread.sleep

getcurrent = greenlet.getcurrent
GreenletExit = greenlet.GreenletExit

spew = debug.spew
unspew = debug.unspew


def named (name):
    """Return an object given its name.

    The name uses a module-like syntax, eg::

      os.path.join

    or::

      mulib.mu.Resource
    """
    toimport = name
    obj = None
    import_err_strings = []
    while toimport:
        try:
            obj = __import__(toimport)
            break
        except ImportError, err:
            # print 'Import error on %s: %s' % (toimport, err)  # debugging spam
            import_err_strings.append(err.__str__())
            toimport = '.'.join(toimport.split('.')[:-1])
    if obj is None:
        raise ImportError(
            '%s could not be imported.  Import errors: %r' % (name, import_err_strings))
    for seg in name.split('.')[1:]:
        try:
            obj = getattr(obj, seg)
        except AttributeError:
            dirobj = dir(obj)
            dirobj.sort()
            raise AttributeError('attribute %r missing from %r (%r) %r.  Import errors: %r' % (
                seg, obj, dirobj, name, import_err_strings))
    return obj

