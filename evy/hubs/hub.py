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

import heapq
import math
import traceback
import signal
import sys
import os

from evy.uv.interface import libuv, handle_unref
from evy.uv.interface import ffi
from evy.uv import watchers
from evy.support import greenlets as greenlet, clear_sys_exc_info
from evy.hubs import timer
from evy import patcher


arm_alarm = None
if hasattr(signal, 'setitimer'):
    def alarm_itimer (seconds):
        signal.setitimer(signal.ITIMER_REAL, seconds)

    arm_alarm = alarm_itimer
else:
    try:
        import itimer

        arm_alarm = itimer.alarm
    except ImportError:
        def alarm_signal (seconds):
            signal.alarm(math.ceil(seconds))

        arm_alarm = alarm_signal

time = patcher.original('time')

g_prevent_multiple_readers = True

READ = "read"
WRITE = "write"



def alarm_handler (signum, frame):
    import inspect
    raise RuntimeError("Blocking detector ALARMED at" + str(inspect.getframeinfo(frame)))

def signal_checker(uv_prepare_handle, status):
    pass  # XXX: how do I check for signals from pure python??



####################################################################################################

_default_loop_destroyed = False


class BaseHub(object):
    """
    Base hub class for easing the implementation of subclasses that are
    specific to a particular underlying event architecture.
    """

    SYSTEM_EXCEPTIONS = (KeyboardInterrupt, SystemExit)

    READ = READ
    WRITE = WRITE

    error_handler = None


    def __init__ (self, clock = time.time, ptr = None, default = True):
        """

        :param clock:
        :type clock:
        :param default: default loop
        :type default: boolean
        :param ptr: a pointer a an (optional) libuv loop
        :type ptr: a "uv_loop_t*"
        """
        self.fd_read_watchers = {}
        self.fd_write_watchers = {}

        self.fd_read_watchers_alt = {}
        self.fd_write_watchers_alt = {}

        self.clock = clock
        self.greenlet = greenlet.greenlet(self.run)

        self.stopping = False
        self.running = False

        self.timers = set()

        self.debug_exceptions = True
        self.debug_blocking = False
        self.debug_blocking_resolution = 1

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
                handle_unref(self._signal_checker)

            else:
                self._uv_ptr = libuv.uv_loop_new()
                if not self._uv_ptr:
                    raise SystemError("uv_loop_new() failed")

    def block_detect_pre (self):
        # shortest alarm we can possibly raise is one second
        tmp = signal.signal(signal.SIGALRM, alarm_handler)
        if tmp != alarm_handler:
            self._old_signal_handler = tmp

        arm_alarm(self.debug_blocking_resolution)

    def block_detect_post (self):
        if (hasattr(self, "_old_signal_handler") and
            self._old_signal_handler):
            signal.signal(signal.SIGALRM, self._old_signal_handler)
        signal.alarm(0)

    def add (self, evtype, fileno, cb):
        """
        Signals an intent to or write a particular file descriptor.

        The *evtype* argument is either the constant READ or WRITE.

        The *fileno* argument is the file number of the file of interest.

        The *cb* argument is the callback which will be called when the file
        is ready for reading/writing.
        """
        if fileno < 0:
            raise ValueError('invalid file descriptor: %d' % (fileno))

        events = 0
        if evtype == READ:
            events = libuv.UV_READABLE
            bucket = self.fd_read_watchers
        elif evtype == WRITE:
            events = libuv.UV_WRITABLE
            bucket = self.fd_write_watchers

        listener = watchers.Poll(self, fileno, events)

        if fileno in bucket:
            if g_prevent_multiple_readers:
                raise RuntimeError("Second simultaneous %s on fileno %s "\
                                   "detected.  Unless you really know what you're doing, "\
                                   "make sure that only one greenthread can %s any "\
                                   "particular socket.  Consider using a pools.Pool. "\
                                   "If you do know what you're doing and want to disable "\
                                   "this error, call "\
                                   "evy.debug.hub_multiple_reader_prevention(False)" % (
                    evtype, fileno, evtype))

            # store off the second listener in another structure
            if evtype == READ:      self.fd_read_watchers_alt.setdefault(fileno, []).append(listener)
            elif evtype == WRITE:   self.fd_write_watchers_alt.setdefault(fileno, []).append(listener)

        else:
            bucket[fileno] = listener

        ## register the listener with libuv
        listener.start(cb, listener)

        return listener

    def remove (self, listener):
        """
        Remove a listener

        :param listener: the listener to remove
        """
        fileno = listener.fileno
        events = listener.events

        if events == libuv.UV_READABLE:             self.fd_read_watchers.pop(fileno, None)
        else:                                       self.fd_write_watchers.pop(fileno, None)

        # migrate a secondary listener to be the primary listener
        if (fileno in self.fd_read_watchers) or (fileno in self.fd_write_watchers):
            if events == libuv.UV_READABLE:         sec = self.fd_read_watchers.get(fileno, None)
            else:                                   sec = self.fd_write_watchers.get(fileno, None)

            if not sec:
                return

            if events == libuv.UV_READABLE:         self.fd_read_watchers[fileno] = sec.pop(0)
            else:                                   self.fd_write_watchers[fileno] = sec.pop(0)

            if not sec:
                if events == libuv.UV_READABLE:     del self.fd_read_watchers[fileno]
                else:                               del self.fd_write_watchers[fileno]

    def remove_descriptor (self, fileno):
        """
        Completely remove all watchers for this *fileno*. For internal use only.
        """
        watchers = []

        watchers.append(self.fd_read_watchers.pop(fileno, None))
        watchers.append(self.fd_write_watchers.pop(fileno, None))

        watchers.extend(self.fd_read_watchers_alt.pop(fileno, ()))
        watchers.extend(self.fd_write_watchers_alt.pop(fileno, ()))
        
        for listener in watchers:
            try:
                listener.cb(fileno)
            except Exception, e:
                self.squelch_generic_exception(sys.exc_info())

        ## remove the poller for this fileno
        # TODO

    def get_readers (self):
        return self.fd_read_watchers.values()

    def get_writers (self):
        return self.fd_write_watchers.values()


    def _get_reader_for(self, fileno):
        """
        Obtains the reader for the file descriptor *fileno*

        :param fileno: the file descriptor
        :return: a valid Poll instance, or None otherwise
        """
        readers = self.fd_watchers[READ]
        return readers.get(fileno, None)

    def _get_writer_for(self, fileno):
        """
        Obtains the writer for the file descriptor *fileno*

        :param fileno: the file descriptor
        :return: a valid Poll instance, or None otherwise
        """
        readers = self.fd_watchers[WRITE]
        return readers.get(fileno, None)


    def set_timer_exceptions (self, value):
        self.debug_exceptions = value


    def ensure_greenlet (self):
        if self.greenlet.dead:
            # create new greenlet sharing same parent as original
            new = greenlet.greenlet(self.run, self.greenlet.parent)
            # need to assign as parent of old greenlet
            # for those greenlets that are currently
            # children of the dead hub and may subsequently
            # exit without further switching to hub.
            self.greenlet.parent = new
            self.greenlet = new

    def switch (self):
        """
        Switches to a different greenlet
        :return:
        :rtype:
        """
        cur = greenlet.getcurrent()
        assert cur is not self.greenlet, 'Cannot switch to MAINLOOP from MAINLOOP'
        switch_out = getattr(cur, 'switch_out', None)
        if switch_out is not None:
            try:
                switch_out()
            except:
                self.squelch_generic_exception(sys.exc_info())
        self.ensure_greenlet()
        try:
            if self.greenlet.parent is not cur:
                cur.parent = self.greenlet
        except ValueError:
            pass  # gets raised if there is a greenlet parent cycle
        clear_sys_exc_info()
        return self.greenlet.switch()

    def wait (self, seconds = None):
        """
        This timeout will cause us to return from the dispatch() call when we want to

        :param seconds: the amount of seconds to wait
        :type seconds: integer
        """

        ## create a timer for avoiding exiting the loop for *seconds*
        timer = watchers.Timer(self, seconds * 1000)
        timer.start(None)

        try:
            status = self.loop(once = True)
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

        if self.debug_blocking:
            self.block_detect_post()


    def default_sleep (self):
        return 10.0

    def sleep_until (self):
        t = self.timers
        if not t:
            return None
        return t[0][0]

    def run (self, *a, **kw):
        """
        Run the loop until abort is called.
        """

        # accept and discard variable arguments because they will be
        # supplied if other greenlets have run and exited before the
        # hub's greenlet gets a chance to run
        if self.running:
            raise RuntimeError("Already running!")
        try:
            self.running = True
            self.stopping = False
            while not self.stopping:

                if self.debug_blocking:
                    self.block_detect_pre()

                if self.debug_blocking:
                    self.block_detect_post()

                try:
                    status = self.loop(once = True)
                except self.SYSTEM_EXCEPTIONS:
                    self.interrupted = True
                except:
                    self.squelch_exception(-1, sys.exc_info())

                ## if there are no active events, just get out of here...
                if self.num_active == 0:
                    self.stopping = True
            else:
                self.timers = set()

        finally:
            self.running = False
            self.stopping = False


    def loop(self, once = False):
        """
        Loop the events

        :param once: if True, runs only once
        :return: None
        """
        if once:    libuv.uv_run_once(self._uv_ptr)
        else:       libuv.uv_run(self._uv_ptr)

    def abort (self, wait = False):
        """
        Stop the loop. If run is executing, it will exit after completing the next loop iteration.

        Set *wait* to True to cause abort to switch to the hub immediately and wait until it's
        finished processing.  Waiting for the hub will only work from the main greenthread; all
        other greenthreads will become unreachable.
        """
        if self.running:
            self.stopping = True
        if wait:
            assert self.greenlet is not greenlet.getcurrent(), "Can't abort with wait from inside the hub's greenlet."
            # schedule an immediate timer just so the hub doesn't sleep
            self.schedule_call_global(0, lambda: None)
            # switch to it; when done the hub will switch back to its parent,
            # the main greenlet
            self.switch()

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

    @property
    def num_active(self):
        return self._uv_ptr.active_handles

    @property
    def last_error(self):
        return self._uv_ptr.last_err

    ##
    ## timers
    ##

    def add_timer (self, timer):
        """
        Add a timer in the hub

        :param timer:
        :param unreferenced: if True, we unreference the timer, so the loop does not wait until it is triggered
        :return:
        """
        eventtimer = watchers.Timer(self, timer.seconds * 1000)
        timer.impltimer = eventtimer
        eventtimer.start(self.timer_triggered, timer)
        self.timers.add(timer)

    def timer_canceled (self, timer):
        """
        A timer has been canceled

        :param timer: the timer that has been canceled
        :return: nothing
        """
        try:
            timer.destroy()
        except (AttributeError, TypeError):
            pass

        try:
            self.timers.remove(timer)
        except ValueError:
            pass

    def timer_triggered (self, timer):
        """
        Performs the timer trigger

        :param timer: the timer that has been triggered
        :return: nothing
        """
        try:
            timer()
        except self.SYSTEM_EXCEPTIONS:
            self.interrupted = True
        except:
            self.squelch_exception(-1, sys.exc_info())

        try:
            timer.destroy()
            self.timers.remove(timer)
        except (AttributeError, TypeError):
            pass

    def forget_timer(self, timer):
        """
        Let the hub forget about a timer, so we do not keep the loop running forever until
        this timer triggers...
        """
        try:
            self.unref(timer.impltimer.handle)
        except (AttributeError, TypeError):
            pass

    @property
    def timers_count(self):
        return len(self.timers)

    ##
    ## global and local calls
    ##

    def schedule_call_local (self, seconds, cb, *args, **kw):
        """
        Schedule a callable to be called after 'seconds' seconds have
        elapsed. Cancel the timer if greenlet has exited.

        :param seconds: the number of seconds to wait.
        :param cb: the callable to call after the given time.
        :param args: arguments to pass to the callable when called.
        :param kw: keyword arguments to pass to the callable when called.
        """
        t = timer.LocalTimer(seconds, cb, *args, **kw)
        self.add_timer(t)
        return t

    def schedule_call_global (self, seconds, cb, *args, **kw):
        """
        Schedule a callable to be called after 'seconds' seconds have
        elapsed. The timer will NOT be canceled if the current greenlet has
        exited before the timer fires.

        :param seconds: the number of seconds to wait.
        :param cb: the callable to call after the given time.
        :param args: arguments to pass to the callable when called.
        :param kw: keyword arguments to pass to the callable when called.

        """
        t = timer.Timer(seconds, cb, *args, **kw)
        self.add_timer(t)
        return t

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

    @property
    def default_loop(self):
        """
        The default events loop

        :return: the default events loop
        """
        return libuv.uv_default_loop()

    ##
    ## references
    ##

    def ref(self, handle):
        """
        The event loop only runs as long as there are active watchers. This system works by having
        every watcher increase the reference count of the event loop when it is started and decreasing
        the reference count when stopped. But it is also possible to manually change the reference
        count of watchers with :method:ref: and :method:unref:

        :return: None
        """
        assert ffi.typeof(handle) is ffi.typeof("uv_handle_t *")
        libuv.uv_ref(handle)

    def unref(self, handle):
        """
        This method can be used with interval timers. You might have a garbage collector which runs
        every X seconds, or your network service might send a heartbeat to others periodically, but
        you don't want to have to stop them along all clean exit paths or error scenarios. Or you
        want the program to exit when all your other watchers are done. In that case just unref() the
        timer immediately after creation so that if it is the only watcher running then uv_run will
        still exit.

        :return: None
        """
        assert ffi.typeof(handle) is ffi.typeof("uv_handle_t *")
        libuv.uv_unref(handle)


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
        return watchers.Poll(self, fd, events, ref)

    def timer(self, after, repeat=0.0, ref=True):
        return watchers.Timer(self, after, repeat, ref)

    def signal(self, signum, ref=True):
        return watchers.Signal(self, signum, ref)

    def idle(self, ref=True):
        return watchers.Idle(self, ref)

    def prepare(self, ref=True):
        return watchers.Prepare(self, ref)

    def async(self, ref=True):
        return watchers.Async(self, ref)

    def callback(self):
        return watchers.Callback(self)

    def run_callback(self, func, *args, **kw):
        result = watchers.Callback(self)
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
    ## exceptions
    ##

    def squelch_exception (self, fileno, exc_info):
        traceback.print_exception(*exc_info)
        sys.stderr.write("Removing descriptor: %r\n" % (fileno,))
        sys.stderr.flush()
        try:
            self.remove_descriptor(fileno)
        except Exception, e:
            sys.stderr.write("Exception while removing descriptor! %r\n" % (e,))
            sys.stderr.flush()

    def squelch_generic_exception (self, exc_info):
        if self.debug_exceptions:
            traceback.print_exception(*exc_info)
            sys.stderr.flush()
            clear_sys_exc_info()

    def squelch_timer_exception (self, timer, exc_info):
        if self.debug_exceptions:
            traceback.print_exception(*exc_info)
            sys.stderr.flush()
            clear_sys_exc_info()

    ##
    ## signals
    ##

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

