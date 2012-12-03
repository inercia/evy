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

from functools import partial

from evy.support import greenlets as greenlet
from evy.hubs import get_hub


## If true, captures a stack trace for each timer when constructed.  This is
## useful for debugging leaking timers, to find out where the timer was set up.
_g_debug = False


class Timer(object):
    """
    A global timer
    """

    def __init__(self, seconds, cb, *args, **kw):
        """
        Create a timer.

        :param seconds: the minimum number of seconds to wait before calling
        :param cb: The callback to call when the timer has expired
        :param *args: the arguments to pass to cb
        :param **kw: the keyword arguments to pass to cb

        This timer will not be run unless it is scheduled in a runloop by
        calling timer.schedule() or runloop.add_timer(timer).
        """
        self.seconds = seconds
        if '_callback' in kw:       self.callback = kw.pop('_callback')
        else:                       self.callback = partial(cb, *args, **kw)

        self.called = False

        if _g_debug:
            import traceback, cStringIO
            self.traceback = cStringIO.StringIO()
            traceback.print_stack(file = self.traceback)

    @property
    def pending(self):
        return not self.called

    def __repr__(self):
        secs = getattr(self, 'seconds', None)
        cb = getattr(self, 'callback', None)
        retval =  "<Timer at %s (after=%s, callback=%s)>" % (hex(id(self)), secs, cb)
        if _g_debug and hasattr(self, 'traceback'):
            retval += '\n' + self.traceback.getvalue()
        return retval

    def copy(self):
        return self.__class__(self.seconds, None, _callback = self.callback)

    def schedule(self):
        """
        Schedule this timer to run in the current loop.
        """
        self.called = False
        self.scheduled_time = get_hub().add_timer(self)
        return self

    def destroy(self):
        """
        Stop and destroy the timer

        Invoke this method when this timer is no longer used
        """
        def _dummy(*args): pass

        self.impltimer.stop()
        self.impltimer.close(_dummy)
        del self.impltimer

    def forget(self):
        """
        Let the hub forget about this timer, so we do not keep the loop running forever until
        the timer triggers.
        """
        get_hub().forget_timer(self)

    def __call__(self, *args):
        if not self.called:
            self.called = True
            try:
                self.callback()
            finally:
                try:
                    del self.callback
                except AttributeError:
                    pass

    def cancel(self):
        """
        Prevent this timer from being called. If the timer has already
        been called or canceled, has no effect.
        """
        if not self.called:
            self.called = True
            get_hub()._timer_canceled(self)
            try:
                del self.callback
            except AttributeError:
                pass

    # No default ordering in 3.x. heapq uses <
    # FIXME should full set be added?
    def __lt__(self, other):
        return id(self)<id(other)


class LocalTimer(Timer):

    def __init__(self, *args, **kwargs):
        self.greenlet = greenlet.getcurrent()
        Timer.__init__(self, *args, **kwargs)

    @property
    def pending(self):
        if self.greenlet is None or self.greenlet.dead:
            return False
        return not self.called

    def __call__(self, *args):
        if not self.called:
            self.called = True
            if self.greenlet is not None and self.greenlet.dead:
                return
            self.callback()

    def cancel(self):
        """
        Cancel the timer
        """
        self.greenlet = None
        Timer.cancel(self)
