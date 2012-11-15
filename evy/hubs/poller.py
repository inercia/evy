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

from functools import partial

from evy.hubs import get_hub
from evy.uv import watchers
from evy.uv.interface import libuv


__all__ = [
    'Poller',
    ]



## If true, captures a stack trace for each poller when constructed.  This is
## useful for debugging leaking pollers, to find out where the poller was set up.
_g_debug = False


class Poller(object):
    """
    A I/O poller
    """

    def __init__(self, fileno, persistent = False, **kw):
        """
        Create a poller.

        :param fileno: the file descriptor we are going to poll
        :param cb: the callback to call when we have detected we can read/write from this file descriptor
        :param *args: the arguments to pass to cb
        :param **kw: the keyword arguments to pass to cb

        This poller will not be run unless it is scheduled in a hub by get_hub().add_poller(poller).
        """
        if fileno < 0:
            raise ValueError('invalid file descriptor: %d' % (fileno))

        self.fileno = fileno
        self.persistent = persistent
        self.impl = None
        self.started = False
        self.read_callback = kw.pop('_read_callback', None)
        self.write_callback = kw.pop('_write_callback', None)
        self.impl = watchers.Poll(get_hub(), fileno)

        if _g_debug:
            import traceback, cStringIO
            self.traceback = cStringIO.StringIO()
            traceback.print_stack(file = self.traceback)


    def __repr__(self):

        events = ''
        if self.read_callback: events += 'R'
        if self.write_callback: events += 'W'

        retval =  "Poller(%d, '%s')" % (self.fileno, events)

        if _g_debug and hasattr(self, 'traceback'):
            retval += '\n' + self.traceback.getvalue()
        return retval

    def copy(self):
        return self.__class__(self.fileno,
                              persistent = self.persistent,
                              _read_callback = self.read_callback,
                              _write_callback = self.write_callback)

    def start(self, hub, event, cb, *args):
        """
        Start the poller for an event on that file descriptor

        :param hub: the hub where this watcher is registered
        :param cb: the callback
        :param args: the arguments for the callback
        :return: the underlying watcher
        """
        assert self.impl is not None
        assert event in [libuv.UV_READABLE, libuv.UV_WRITABLE]

        try:
            self.impl.start(event, hub._poller_triggered, event, self)
        except:
            pass
        else:
            cb = partial(cb, *args)
            if event is libuv.UV_READABLE:  self.read_callback  = cb
            else:                           self.write_callback = cb

        return self.impl


    def cancel(self):
        """
        Prevent this poller from being called. If the poller has already
        been called or canceled, has no effect.
        """
        try:
            if self.notify_readable:   self.read_callback = None
            if self.notify_writable:   self.write_callback = None
        except AttributeError:
            pass

        get_hub()._poller_canceled(self)

    def destroy(self):
        """
        Stop and destroy the poller

        Invoke this method when this poller is no longer used
        """
        self.read_callback = self.write_callback = None

        assert self.impl
        self.impl.stop()
        del self.impl

    def forget(self):
        """
        Let the hub forget about this poller, so we do not keep the loop running forever until
        the poller triggers.
        """
        get_hub().forget_poller(self)


    @property
    def notify_readable(self):
        return self.read_callback is not None

    @property
    def notify_writable(self):
        return self.write_callback is not None

    ##
    ## callbacks
    ##

    def __call__(self, evtype):
        if self.notify_readable and evtype is libuv.UV_READABLE:   self.read_callback()
        if self.notify_writable and evtype is libuv.UV_WRITABLE:   self.write_callback()

    # No default ordering in 3.x. heapq uses <
    # FIXME should full set be added?
    def __lt__(self, other):
        return id(self)<id(other)

