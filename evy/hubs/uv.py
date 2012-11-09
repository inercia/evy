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

from __future__ import absolute_import

import os
import sys
import traceback
import time

from evy.hubs import hub
from evy.uv.interface import libuv
from evy.uv.watchers import Poll, Timer, Async, Callback, Idle, Prepare, Signal


from evy.uv.interface import ffi


################################################################################################################



_default_loop_destroyed = False

def signal_checker(uv_prepare_handle, status):
    pass  # XXX: how do I check for signals from pure python??



class Hub(hub.BaseHub):
    """
    A UV hub
    """

    error_handler = None

    def __init__(self, clock = time.time, ptr = None, default = True):
        """
        Initialize a default loop

        :param default: default loop
        :type default: boolean
        :param ptr: a pointer a an (optional) libuv loop
        :type ptr: a "uv_loop_t*"
        :param clock:
        :type clock:
        """
        super(Hub, self).__init__(clock)
        self.interrupted = False

        if ptr:
            assert ffi.typeof(ptr) is ffi.typeof("uv_loop_t *")
            self._uv_ptr = ptr
        else:
            if _default_loop_destroyed:
                default = False
            if default:
                self._uv_ptr = libuv.uv_default_loop()
                if not self._uv_ptr:
                    raise SystemError("uv_default_loop() failed")

                self._signal_checker = ffi.new("uv_prepare_t *")
                self._signal_checker_cb = ffi.callback("void(*)(uv_prepare_t *, int)", signal_checker)

                libuv.uv_prepare_init(self._uv_ptr, self._signal_checker)
                libuv.uv_prepare_start(self._signal_checker, self._signal_checker_cb)
                #libuv.uv_unref(self._uv_ptr)

            else:
                self._uv_ptr = libuv.uv_loop_new()
                if not self._uv_ptr:
                    raise SystemError("uv_loop_new() failed")

                    #if default or __SYSERR_CALLBACK is None:
                    #    set_syserr_cb(self._handle_syserr)

    def add (self, evtype, fileno, cb):
        """
        Watch a new file descriptor, invoking the *cb* when it is available for reading or writting,
        depending on the events we are interested in.

        :param evtype: the events we are interested in
        :param fileno: the file descriptor
        :param cb: the callback
        :return: the listener
        """
        listener = super(Hub, self).add(evtype, fileno, cb)

        events = 0
        if evtype & hub.READ:    events |= libuv.UV_READABLE
        if evtype & hub.WRITE:   events |= libuv.UV_WRITABLE

        if events != 0:
            evt = Poll(self, fileno, events)
            evt.start()

        return listener


    def run(self, once=False):
        """
        Run the event loop

        :param once: if True, runs only once
        :return: None
        """
        if once:
            libuv.uv_run_once(self._uv_ptr)
        else:
            libuv.uv_run(self._uv_ptr)

    def abort(self):
        """
        Abort the event loop execution

        :return:
        """
        super(Hub, self).abort()
        print "abort(): TODO"

    def destroy(self):
        """
        Destroy the events loop

        :return: None
        """
        global _default_loop_destroyed
        if self._uv_ptr:
            self._stop_signal_checker()
            #if __SYSERR_CALLBACK == self._handle_syserr:
            #    set_syserr_cb(None)
            if libuv.uv_is_default_loop(self._uv_ptr):
                _default_loop_destroyed = True
            libuv.uv_loop_destroy(self._uv_ptr)
            self._uv_ptr = ffi.NULL

    def wait(self, seconds = None):
        # this timeout will cause us to return from the dispatch() call
        # when we want to

        timer = Timer(self, seconds)
        timer.start(lambda x: None)

        try:
            status = self.run(once = True)
        except self.SYSTEM_EXCEPTIONS:
            self.interrupted = True
        except:
            self.squelch_exception(-1, sys.exc_info())

        # we are explicitly ignoring the status because in our experience it's
        # harmless and there's nothing meaningful we could do with it anyway

        timer.stop()


        # raise any signals that deserve raising
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt()


    @property
    def default_loop(self):
        """
        The default events loop

        :return: the default events loop
        """
        return libuv.uv_default_loop()

    ##
    ## timers
    ##

    def add_timer(self, timer):
        # store the pyevent timer object so that we can cancel later
        eventtimer = Timer(self, timer.seconds)
        timer.impltimer = eventtimer
        eventtimer.start(self.timer_finished, timer)

    def timer_finished(self, timer):
        #timer.impltimer.stop()
        del timer.impltimer
        #try:
        #    timer.impltimer.stop()
        #    del timer.impltimer
        #except (AttributeError, TypeError):     # TODO: might this raise other errors?
        #    pass
        #finally:
        #    super(Hub, self).timer_finished(timer)

    def timer_canceled(self, timer):
        """
        Cancels the underlying libevent timer.
        """
        #timer.impltimer.stop()
        del timer.impltimer
        #try:
        #    timer.impltimer.stop()
        #    del timer.impltimer
        #except (AttributeError, TypeError):
        #    pass
        #finally:
        #    super(Hub, self).timer_canceled(timer)


    ##
    ## internals
    ##

    @property
    def ptr(self):
        """
        The internal libuv `uv_loop_t*`

        :return: a pointer to the corresponding `uv_loop_t*`
        """
        return self._uv_ptr

    def _stop_signal_checker(self):
        if libuv.uv_is_active(self._signal_checker):
            libuv.uv_ref(self._uv_ptr)
            libuv.uv_prepare_stop(self._signal_checker)

    def signal_received(self, signal):
        # can't do more than set this flag here because the pyevent callback
        # mechanism swallows exceptions raised here, so we have to raise in
        # the 'main' greenlet (in wait()) to kill the program
        self.interrupted = True
        print "signal_received(): TODO"


    ##
    ## errors
    ##

    def _handle_syserr(self, message, errno):
        self.handle_error(None, SystemError, SystemError(message + ': ' + os.strerror(errno)), None)

    def handle_error(self, context, type, value, tb):
        handle_error = None
        error_handler = self.error_handler
        if error_handler is not None:
            # we do want to do getattr every time so that setting Hub.handle_error property just works
            handle_error = getattr(error_handler, 'handle_error', error_handler)
            handle_error(context, type, value, tb)
        else:
            self._default_handle_error(context, type, value, tb)

    def _default_handle_error(self, context, type, value, tb):
        traceback.print_exception(type, value, tb)
        sys.abort()
        raise NotImplementedError()


    ##
    ## references
    ##

    def ref(self):
        """
        The event loop only runs as long as there are active watchers. This system works by having
        every watcher increase the reference count of the event loop when it is started and decreasing
        the reference count when stopped. But it is also possible to manually change the reference
        count of watchers with :method:ref: and :method:unref:

        :return: None
        """
        libuv.uv_ref(self._uv_ptr)

    def unref(self):
        """
        This method can be used with interval timers. You might have a garbage collector which runs
        every X seconds, or your network service might send a heartbeat to others periodically, but
        you don't want to have to stop them along all clean exit paths or error scenarios. Or you
        want the program to exit when all your other watchers are done. In that case just unref() the
        timer immediately after creation so that if it is the only watcher running then uv_run will
        still exit.

        :return: None
        """
        libuv.uv_unref(self._uv_ptr)


    def now(self):
        return libuv.uv_now(self._uv_ptr)

    def XXX__repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), self._format())


    ##
    ## constructors
    ##

    @property
    def WatcherType(self):
        from evy.uv.watchers import Watcher
        return Watcher

    def io(self, fd, events, ref=True):
        return Poll(self, fd, events, ref)

    def timer(self, after, repeat=0.0, ref=True):
        return Timer(self, after, repeat, ref)

    def signal(self, signum, ref=True):
        return Signal(self, signum, ref)

    def idle(self, ref=True):
        return Idle(self, ref)

    def prepare(self, ref=True):
        return Prepare(self, ref)

    def async(self, ref=True):
        return Async(self, ref)

    def callback(self):
        return Callback(self)

    def run_callback(self, func, *args, **kw):
        result = Callback(self)
        result.start(func, *args)
        return result

    def _format(self):
        msg = self.backend
        if self.default:
            msg += ' default'
        return msg

    def fileno(self):
        fd = self._uv_ptr.backend_fd
        if fd >= 0:
            return fd

