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
from evy.hubs import get_hub


class Callback(object):
    """
    A global callback
    """

    __slots__ = [
        'callback',
        'called',
        'implcallback',
    ]

    def __init__(self, cb, *args, **kw):
        """
        Create a callback for being invoked at the end of the loop.
        :param cb: The callback to call
        :param *args: the arguments to pass to cb
        :param **kw: the keyword arguments to pass to cb
        """
        self.called = False

        if '_callback' in kw:
            self.callback = kw.pop('_callback')
        else:
            self.callback = partial(cb, *args, **kw)

    @property
    def pending(self):
        return not self.called

    def __repr__(self):
        secs = getattr(self, 'seconds', None)
        cb = getattr(self, 'callback', None)
        retval =  "<Callback at %s (after=%s, callback=%s)>" % (hex(id(self)), secs, cb)
        return retval

    def copy(self):
        return self.__class__(None, _callback = self.callback)

    def schedule(self):
        """
        Schedule this callback to run in the current loop.
        """
        self.called = False
        return get_hub().add_callback(self)

    def __del__(self):
        self.destroy()

    def destroy(self):
        """
        Stop and destroy the callback
        """
        if hasattr(self, 'implcallback'):
            self.implcallback.stop()

            def _dummy(*args): pass
            self.implcallback.close(_dummy)

            del self.implcallback
            del self.callback

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
        Prevent this idle from being called. If the callback has already
        been called or canceled, has no effect.
        """
        if not self.called:
            self.called = True
            get_hub()._callback_canceled(self)
            try:
                del self.callback
            except AttributeError:
                pass

    # No default ordering in 3.x. heapq uses <
    # FIXME should full set be added?
    def __lt__(self, other):
        return id(self)<id(other)
