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
from evy.hubs.hub import READ, WRITE
from evy.uv import watchers
from evy.uv.interface import libuv

## If true, captures a stack trace for each poller when constructed.  This is
## useful for debugging leaking pollers, to find out where the poller was set up.
_g_debug = False


class Poller(object):
    """
    A I/O poller
    """

    def __init__(self, fileno, evtype, persistent = False, read_cb = None, write_cb = None, **kw):
        """
        Create a poller.

        :param fileno: the file descriptor we are going to poll
        :param cb: The callback to call when we have detected we can use this file descriptor for reading or writting
        :param *args: the arguments to pass to cb
        :param **kw: the keyword arguments to pass to cb

        This poller will not be run unless it is scheduled in a hub by get_hub().add_poller(poller).
        """

        if fileno < 0:
            raise ValueError('invalid file descriptor: %d' % (fileno))
        else:
            self.fileno = fileno

        self.persistent = persistent

        if '_read_callback' in kw:  self.read_callback = kw.pop('_read_callback')
        else:                       self.read_callback = partial(read_cb, fileno)

        if '_write_callback' in kw: self.write_callback = kw.pop('_write_callback')
        else:                       self.write_callback = partial(write_cb, fileno)

        if '_events' in kw:
            self._events = kw.pop('_events')
        else:
            self._events = 0
            if evtype == READ:
                self._events = libuv.UV_READABLE
            elif evtype == WRITE:
                self._events = libuv.UV_WRITABLE

        if _g_debug:
            import traceback, cStringIO
            self.traceback = cStringIO.StringIO()
            traceback.print_stack(file = self.traceback)


    def __repr__(self):
        secs = getattr(self, 'seconds', None)
        cb = getattr(self, 'callback', None)
        retval =  "Poller(%s, %s)" % (secs, cb)
        if _g_debug and hasattr(self, 'traceback'):
            retval += '\n' + self.traceback.getvalue()
        return retval

    def copy(self):
        return self.__class__(self.fileno, None,
                              persistent = self.persistent,
                              _events = self._events,
                              _read_callback = self.read_callback,
                              _write_callback = self.write_callback)

    def cancel(self):
        """
        Prevent this poller from being called. If the poller has already
        been called or canceled, has no effect.
        """
        try:
            if self._events & libuv.UV_READABLE:    del self.read_callback
            if self._events & libuv.UV_WRITEABLE:   del self.write_callback
        except AttributeError:
            pass

        get_hub()._poller_canceled(self)

    def destroy(self):
        """
        Stop and destroy the poller

        Invoke this method when this poller is no longer used
        """
        self.implpoller.stop()
        del self.implpoller

    def forget(self):
        """
        Let the hub forget about this poller, so we do not keep the loop running forever until
        the poller triggers.
        """
        get_hub().forget_poller(self)


    ##
    ## the events we are watching
    ##

    def _set_events(self, event):
        new_events = self._events
        if event == READ:       new_events |= libuv.UV_READABLE
        elif event == WRITE:    new_events |= libuv.UV_WRITABLE

        ## TODO: update the events we are polling here...

    def _get_events(self):
        return self._events

    events = property(_get_events, _set_events)


    ##
    ## callbacks
    ##

    def __call__(self, *args):
        try:
            if self._events & libuv.UV_READABLE:    self.read_callback()
            if self._events & libuv.UV_WRITEABLE:   self.write_callback()
        finally:
            try:
                if not self.persistent:
                    if self._events & libuv.UV_READABLE:    del self.read_callback
                    if self._events & libuv.UV_WRITEABLE:   del self.write_callback
            except AttributeError:
                pass

    # No default ordering in 3.x. heapq uses <
    # FIXME should full set be added?
    def __lt__(self, other):
        return id(self)<id(other)

