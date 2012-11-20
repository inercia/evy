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

import math
import traceback
import signal
import sys
import os

from evy.uv.interface import libuv, handle_unref
from evy.uv.interface import ffi
from evy.uv import watchers
from evy.support import greenlets as greenlet, clear_sys_exc_info
from evy.hubs import timer, poller
from evy import patcher


__all__ = ["Hub",
           "READ",
           "WRITE"]



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





READ = libuv.UV_READABLE
WRITE = libuv.UV_WRITABLE



def alarm_handler (signum, frame):
    import inspect
    raise RuntimeError("Blocking detector ALARMED at" + str(inspect.getframeinfo(frame)))

def _signal_checker(uv_prepare_handle, status):
    pass  # XXX: how do I check for signals from pure python??



####################################################################################################

_default_loop_destroyed = False


class Hub(object):
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
        self.clock = clock
        self.greenlet = greenlet.greenlet(self.run)

        self.stopping = False
        self.running = False

        self.timers = set()
        self.pollers = {}

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
                self._signal_checker_cb = ffi.callback("void(*)(uv_prepare_t *, int)", _signal_checker)

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

    def add (self, evtype, fileno, cb, persistent = False):
        """
        Signals an intent to or write a particular file descriptor.

        :param evtype: either the constant READ or WRITE.
        :param fileno: the file number of the file of interest.
        :param cb: callback which will be called when the file is ready for reading/writing.
        """
        if fileno in self.pollers:
            p = self.pollers[fileno]

            ## check we do not have another callback on the same descriptor and event
            if p.notify_readable and evtype is READ:
                raise RuntimeError('there is already %s reading from descriptor %d' % (str(p), fileno))
            if p.notify_writable and evtype is WRITE:
                raise RuntimeError('there is already %s writing to descriptor %d' % (str(p), fileno))

            p.start(self, evtype, cb, fileno)
        else:
            p = poller.Poller(fileno, persistent = persistent)
            p.start(self, evtype, cb, fileno)

            ## register the poller
            self.pollers[fileno] = p

        return p

    def remove (self, p):
        """
        Remove a listener

        :param listener: the listener to remove
        """
        self._poller_canceled(p)


    def remove_descriptor (self, fileno, skip_callbacks = False):
        """
        Completely remove all watchers for this *fileno*. For internal use only.
        """
        try:
            p = self.pollers[fileno]
        except KeyError:
            return

        try:
            if not skip_callbacks:
                # invoke the callbacks in the poller and destroy it
                p(READ)
                p(WRITE)
        except self.SYSTEM_EXCEPTIONS:
            self.interrupted = True
        except:
            self.squelch_exception(fileno, sys.exc_info())
        finally:
            self._poller_canceled(p)


    def set_timer_exceptions (self, value):
        """
        Debug exceptions

        :param value: True if we want to debug exceptions
        :type value: boolean
        """
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

        if not seconds:
            seconds = self.default_sleep()

        ## create a timer for avoiding exiting the loop for *seconds*
        timer = watchers.Timer(self, seconds * 1000.0)
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

                try:
                    status = self.loop(once = True)
                except self.SYSTEM_EXCEPTIONS:
                    self.interrupted = True
                except:
                    self.squelch_exception(-1, sys.exc_info())

                if self.debug_blocking:
                    self.block_detect_post()

                ## if there are no active events, just get out of here...
                if self.num_active == 0:
                    self.stopping = True
            else:
                ## remove all the timers and pollers
                for timer in self.timers:               timer.destroy()
                for poller in self.pollers.values():    poller.destroy()
                self.timers = set()
                self.pollers = {}

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

            ## destroy all the timers and pollers
            for timer in self.timers:               timer.destroy()
            for poller in self.pollers.values():    poller.destroy()
            self.timers = set()
            self.pollers = {}

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
        eventtimer = watchers.Timer(self, timer.seconds * 1000.0)
        timer.impltimer = eventtimer
        eventtimer.start(self._timer_triggered, timer)
        self.timers.add(timer)

    def _timer_canceled (self, timer):
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
        except KeyError:
            pass

    def _timer_triggered (self, timer):
        """
        Performs the timer trigger

        :param timer: the timer that has been triggered
        :return: nothing
        """
        try:
            timer()
        except self.SYSTEM_EXCEPTIONS:
            self.interrupted = True
        except Exception, e:
            self.squelch_timer_exception(timer, sys.exc_info())

        try:
            timer.destroy()
        except (AttributeError, TypeError):
            pass

        try:
            self.timers.remove(timer)
        except KeyError:
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
    ## pollers
    ##


    def _poller_triggered (self, evtype, p):
        """
        Performs the poller trigger

        :param poller: the poller that has been triggered
        :return: nothing
        """
        try:
            p(evtype)
        except self.SYSTEM_EXCEPTIONS:
            self.interrupted = True
        except:
            self.squelch_exception(p.fileno, sys.exc_info())

        if not p.persistent:
            self._poller_canceled(p)

    def _poller_canceled (self, p):
        """
        A poller has been canceled

        :param poller: the poller that has been canceled
        :return: nothing
        """
        assert p and isinstance(p, poller.Poller)

        fileno = p.fileno

        p.destroy()

        ## remove all references to the poller...
        try:
            del self.pollers[fileno]
        except KeyError:
            pass

        assert fileno not in self.pollers


    def forget_poller(self, poller):
        """
        Let the hub forget about a poller, so we do not keep the loop running forever until
        this poller triggers...
        """
        try:
            self.unref(poller.impltimer.handle)
        except (AttributeError, TypeError):
            pass

    @property
    def poller_count(self):
        return len(self.pollers)

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

    def poller(self, fd, ref=True):
        return watchers.Poll(self, fd, ref)

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
        self.abort()
        #sys.exit(1)

    ##
    ## exceptions
    ##

    def squelch_generic_exception (self, exc_info):
        if self.debug_exceptions:
            traceback.print_exception(*exc_info)
            sys.stderr.flush()
            clear_sys_exc_info()

    def squelch_exception (self, fileno, exc_info):
        traceback.print_exception(*exc_info)

        if fileno > 0:
            try:
                self.remove_descriptor(fileno)
            except Exception, e:
                sys.stderr.write("Exception while removing descriptor! %r\n" % (e,))
                sys.stderr.flush()

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


    ##
    ## readers and writers
    ##
    def get_readers(self):
        return [x for x in self.pollers.values() if x.notify_readable]

    def get_writers(self):
        return [x for x in self.pollers.values() if x.notify_writable]

    def __repr__(self):
        retval =  "Hub(%d pollers, %d timers, %d active)" % (self.poller_count, self.timers_count, self.num_active)
        return retval
