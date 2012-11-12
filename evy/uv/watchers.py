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

import sys
import signal

from functools import partial

from evy.uv.interface import libuv, ffi, handle_is_active, cast_to_handle



class Watcher(object):
    """
    An abstract watcher
    """

    libuv_start_this_watcher = None
    libuv_stop_this_watcher = None
    libuv_handle_type = 'uv_handle_t *'

    hub = None

    _callback = None
    _flags = 0
    _start_func = None
    _stop_func = None


    def __init__(self, _hub, ref = True):
        assert self._uv_handle and self._cb

        self.hub = _hub
        if ref:
            self._flags = 0
        else:
            self._flags = 4

        ## prepare a function for starting the watcher
        if self.libuv_start_this_watcher:
            self._start_func = partial(self.libuv_start_this_watcher, self._uv_handle, self._cb)

        ## .. and another one for stopping it
        if self.libuv_stop_this_watcher:
            self._stop_func = partial(self.libuv_stop_this_watcher, self._uv_handle)

    def _run_callback(self, handle, *args):
        """
        This is invoked as a callback when the watcher completes (for example, when a timer is expired)

        It will call the callback provided on the start() method
        """
        uv_handle = self._cast_libuv_handle(handle)

        if self.callback:
            try:
                self.callback()
            except:
                try:
                    self.hub.handle_error(self, *sys.exc_info())
                finally:
                    #if revents & (libuv.UV_READABLE | libuv.UV_WRITABLE):
                    #    # /* poll watcher: not stopping it may cause the failing callback to be called repeatedly */
                    #    try:
                    #        self.stop()
                    #    except:
                    #        self.hub.handle_error(self, *sys.exc_info())
                    #    return
                    pass

        # callbacks' self.active differs from uv_is_active(...) at this point. don't use it!
        #if not handle_is_active(uv_handle):
        #    self.stop()


    ##
    ## references
    ##

    def _libuv_unref(self):
        #if self._flags & 6 == 4:
        #    libuv.uv_unref(self.hub._uv_ptr)
        #    self._flags |= 2
        pass

    def _python_incref(self):
        #if not self._flags & 1:
        #    # Py_INCREF(<PyObjectPtr>self)
        #    self._flags |= 1
        pass

    def _get_ref(self):
        #return False if self._flags & 4 else True
        pass

    def _set_ref(self, value):
#        if value:
#            if not self._flags & 4:
#                return  # ref is already True
#            if self._flags & 2:  # uv_unref was called, undo
#                libuv.uv_ref(self.hub._uv_ptr)
#            self._flags &= ~6  # do not want unref, no outstanding unref
#        else:
#            if self._flags & 4:
#                return  # ref is already False
#            self._flags |= 4
#            if not self._flags & 2 and self.active:
#                libuv.uv_unref(self.hub._uv_ptr)
#                self._flags |= 2
        pass

    ref = property(_get_ref, _set_ref)

    ##
    ## start/stop
    ##

    def start(self, callback, *args, **kwargs):
        """
        Start the watcher

        :param callback: callback to invoke when the watcher is done
        :param args: arguments for calling the callback
        """
        self.callback = partial(callback, *args, **kwargs)
        self._libuv_unref()

        if self._start_func: self._start_func()

        self._python_incref()

    def stop(self):
        """
        Stop the watcher
        """
        if self._flags & 2:
            libuv.uv_ref(self.hub._uv_ptr)
            self._flags &= ~2

        if self._stop_func: self._stop_func()

        self.callback = None

        if self._flags & 1:
            # Py_DECREF(<PyObjectPtr>self)
            self._flags &= ~1

    @property
    def active(self):
        return handle_is_active(self._uv_handle)

    ##
    ## handles
    ##

    @property
    def handle(self):
        """
        Return the uv_handle for this watcher
        """
        return cast_to_handle(self._uv_handle)

    def _new_libuv_handle(self):
        """
        Return a new libuv C handle for this watcher
        """
        return ffi.new(self.libuv_handle_type)

    def _cast_libuv_handle(self, handle):
        """
        Performs a cast for the handle
        """
        return ffi.cast(self.libuv_handle_type, handle)


class Poll(Watcher):
    """
    This watcher is used to watch file descriptors for readability and writability, similar to the
    purpose of poll(2).

    The purpose is to enable integrating external libraries that rely on the event loop to signal
    it about the socket status changes, like c-ares or libssh2. Using Poll for any other other
    purpose is not recommended; `uv_tcp_t`, `uv_udp_t`, etc. provide an implementation that is much
    faster and more scalable than what can be achieved with uv_poll_t, especially on Windows.

    It is possible that Poll occasionally signals that a file descriptor is readable or writable
    even when it isn't. The user should therefore always be prepared to handle `EAGAIN` or equivalent
    when it attempts to read from or write to the fd.

    It is not okay to have multiple active Poll watchers for the same socket. This can cause
    libuv to busyloop or otherwise malfunction.

    The user should not close a file descriptor while it is being polled by an active Poll watcher.
    This can cause the poll watcher to report an error, but it might also start polling another socket.
    However the fd can be safely closed immediately after a call to uv_poll_stop() or uv_close().

    On windows only sockets can be polled with Poll. On unix any file descriptor that would be
    accepted by poll(2) can be used with Poll.
    """

    libuv_start_this_watcher = None
    libuv_stop_this_watcher = libuv.uv_poll_stop
    libuv_handle_type = 'uv_poll_t *'

    def __init__(self, hub, fd, events, ref = True):
        """
        Initialize the polling watcher

        :param hub: the Hub we arre currently using
        :param fd: the file descriptor
        :param events: the events we are interested in (a combination of Hub.READ and Hub.WRITE)
        """
        if fd < 0:
            raise ValueError('fd must be non-negative: %r' % fd)

        if events & ~(libuv.UV_READABLE | libuv.UV_WRITABLE):
            raise ValueError('illegal event mask: %r' % events)

        self._uv_handle = self._new_libuv_handle()
        self._cb = ffi.callback("void(*)(uv_poll_t *, int, int)", self._run_callback)
        self._events = events
        self._fd = fd

        libuv.uv_poll_init(hub._uv_ptr, self._uv_handle, fd)
        Watcher.__init__(self, hub, ref = ref)

    def start(self, callback, *args, **kwargs):
        """
        Start the file descriptor poller

        :param callback: callback to invoke when the file descriptor is available for the events we wanted
        :param args: arguments for calling the callback
        :param kw: keywords arguments for calling the callback
        :return: None
        """
        self.callback = partial(callback, *args, **kwargs)

        self._libuv_unref()

        libuv.uv_poll_start(self._uv_handle, self._events, self._cb)

        self._python_incref()

    ##
    ## file descriptor
    ##

    def _get_fd(self):
        return self._fd

    def _set_fd(self, fd):
        if self.active:
            raise AttributeError("'poll' watcher attribute 'fd' is read-only while watcher is active")
        self._fd = fd
        libuv.uv_poll_init(self.hub._uv_ptr, self._uv_handle, self._fd)

    fd = property(_get_fd, _set_fd)

    ##
    ## events
    ##

    def _get_events(self):
        return self._events

    def _set_events(self, events):
        if self.active:
            raise AttributeError("'poll' watcher attribute 'events' is read-only while watcher is active")
        self._events = events

    events = property(_get_events, _set_events)

    def _format(self):
        return ' fd=%s events=%s' % (self.fd, self.events_str)



class Timer(Watcher):
    """
    Start a timer. Times are in milliseconds.
    """
    libuv_start_this_watcher = None
    libuv_stop_this_watcher = libuv.uv_timer_stop
    libuv_handle_type = 'uv_timer_t *'

    def __init__(self, hub, after = 0.0, repeat = 0.0, ref = True):
        """
        Initialize a timer

        If *after* is zero, the callback fires on the next tick of the event loop.

        If *repeat* is non-zero, the callback fires first after timeout milliseconds and then repeatedly
        after *repeat* milliseconds.

        *after* and *repeat* are signed integers but that will change in a future version of libuv.
        Don't pass in negative values, you'll get a nasty surprise when that change becomes effective.

        :param after: start time (in milliseconds)
        :param repeat: repetition interval (in milliseconds)
        """
        if repeat < 0.0:
            raise ValueError("repeat must be positive or zero: %r" % repeat)

        self._uv_handle = self._new_libuv_handle()
        self._cb = ffi.callback("void(*)(uv_timer_t *, int)", self._run_callback)
        self._after = after
        self._repeat = repeat

        libuv.uv_timer_init(hub._uv_ptr, self._uv_handle)
        Watcher.__init__(self, hub, ref = ref)

    def start(self, callback, *args, **kwargs):
        """
        Start the timer

        :param callback: callback to invoke when the timer is triggered
        :param args: arguments for calling the callback
        :param kw: keywords arguments for calling the callback
        :return: None
        """
        update = kwargs.get("update", True)
        self.callback = partial(callback, *args, **kwargs)

        self._libuv_unref()

        if update: libuv.uv_update_time(self.hub._uv_ptr)

        libuv.uv_timer_start(self._uv_handle, self._cb, self._after, self._repeat)

        self._python_incref()


    @property
    def at(self):
        """
        Return the time for the timer
        """
        return self._after

    def again(self, callback, *args, **kwargs):
        """
        Stop the timer, and if it is repeating restart it using the repeat value as the timeout.
        """
        update = kwargs.get("update", True)
        self.callback = partial(callback, *args, **kwargs)

        self._libuv_unref()
        if update:
            libuv.uv_now_update(self.hub._uv_ptr)
        ret = libuv.uv_timer_again(self.hub._uv_ptr, self._uv_handle)
        ## TODO: if the timer has never been started before it returns -1 and sets the error to UV_EINVAL.
        self._python_incref()


class Signal(Watcher):
    """
    UNIX signal handling on a per-event loop basis. The implementation is not ultra efficient so
    don't go creating a million event loops with a million signal watchers.

    Some signal support is available on Windows:

      * `SIGINT` is normally delivered when the user presses `CTRL+C`. However, like
        on Unix, it is not generated when terminal raw mode is enabled.

      * `SIGBREAK` is delivered when the user pressed `CTRL+BREAK`.

      * `SIGHUP` is generated when the user closes the console window. On `SIGHUP` the
        program is given approximately 10 seconds to perform cleanup. After that
        Windows will unconditionally terminate it.

      * `SIGWINCH` is raised whenever libuv detects that the console has been
        resized. `SIGWINCH` is emulated by libuv when the program uses an uv_tty_t
        handle to write to the console. `SIGWINCH` may not always be delivered in a
        timely manner; libuv will only detect size changes when the cursor is
        being moved. When a readable uv_tty_handle is used in raw mode, resizing
        the console buffer will also trigger a `SIGWINCH` signal.

    Watchers for other signals can be successfully created, but these signals are never generated.
    These signals are: `SIGILL`, `SIGABRT`, `SIGFPE`, `SIGSEGV`, `SIGTERM` and `SIGKILL`.

    Note that calls to raise() or abort() to programmatically raise a signal are not detected by
    `libuv`; these will not trigger a signal watcher.
    """
    libuv_start_this_watcher = None
    libuv_stop_this_watcher = libuv.uv_signal_stop
    libuv_handle_type = 'uv_signal_t *'

    def __init__(self, hub, signalnum, ref = True):
        """
        Initialize the watcher

        :param hub: a Hub() instance
        :param signalnum: a signal number
        """
        if signalnum < 1 or signalnum >= signal.NSIG:
            raise ValueError('illegal signal number: %r' % signalnum)
            # still possible to crash on one of libuv's asserts:
            # 1) "libuv: uv_signal_start called with illegal signal number"
            #    EV_NSIG might be different from signal.NSIG on some platforms
            # 2) "libuv: a signal must not be attached to two different loops"
            #    we probably could check that in LIBEV_EMBED mode, but not in general

        self._uv_handle = self._new_libuv_handle()
        self._cb = ffi.callback("void(*)(uv_signal_t *, int)", self._run_callback)
        self._signum = signalnum

        libuv.uv_signal_init(hub._uv_ptr, self._uv_handle)
        Watcher.__init__(self, hub, ref = ref)

    def start(self, callback, *args, **kwargs):
        """
        Start the signal watcher

        :param callback: callback to invoke when the signal is detected
        :param args: arguments for calling the callback
        :param kw: keywords arguments for calling the callback
        :return: None
        """
        self.callback = partial(callback, *args, **kwargs)

        self._libuv_unref()

        libuv.uv_signal_start(self._uv_handle, self._cb, self._signum)

        self._python_incref()



class Idle(Watcher):
    """
    Every active idle handle gets its callback called repeatedly until it is stopped. This happens
    after all other types of callbacks are processed. When there are multiple "idle" handles active,
    their callbacks are called in turn.
    """
    libuv_start_this_watcher = libuv.uv_idle_start
    libuv_stop_this_watcher = libuv.uv_idle_stop
    libuv_handle_type = 'uv_idle_t *'

    def __init__(self, hub, ref = True):
        """
        Initialize the watcher

        :param hub: a Hub() instance
        """
        self._uv_handle = self._new_libuv_handle()
        self._cb = ffi.callback("void(*)(uv_idle_t *, int)", self._run_callback)
        libuv.uv_idle_init(hub._uv_ptr, self._uv_handle)
        Watcher.__init__(self, hub, ref = ref)


class Prepare(Watcher):
    """
    Every active prepare handle gets its callback called exactly once per loop iteration, just before
    the system blocks to wait for completed i/o.
    """
    libuv_start_this_watcher = libuv.uv_prepare_start
    libuv_stop_this_watcher = libuv.uv_prepare_stop
    libuv_handle_type = 'uv_prepare_t *'

    def __init__(self, hub, ref=True):
        """
        Initialize the watcher

        :param hub: a Hub() instance
        """
        self._uv_handle = self._new_libuv_handle()
        self._cb = ffi.callback("void(*)(uv_prepare_t *, int)", self._run_callback)
        libuv.uv_prepare_init(hub._uv_ptr, self._uv_handle)
        Watcher.__init__(self, hub, ref = ref)


class Async(Watcher):
    """
    An Async wakes up the event loop and calls the async handle's callback.
    There is no guarantee that every send() call leads to exactly one invocation of the
    callback; the only guarantee is that the callback function is called at least once after the
    call send(). Unlike all other libuv functions, send() can be called from
    another thread.
    """
    libuv_start_this_watcher = libuv.uv_async_send
    libuv_stop_this_watcher = None
    libuv_handle_type = 'uv_sync_t *'

    def __init__(self, hub, ref=True):
        """
        Initialize the watcher

        :param hub: a Hub() instance
        """
        self._uv_handle = self._new_libuv_handle()
        self._cb = ffi.callback("void(*)(uv_async_t *, int)", self._run_callback)
        libuv.uv_async_init(hub._uv_ptr, self._uv_handle, self._cb)
        Watcher.__init__(self, hub, ref = ref)


class Callback(Watcher):
    """
    Pseudo-watcher used to execute a callback in the loop as soon as possible.
    """

    # does not matter which type we actually use, since we are going
    # to feed() events, not start watchers

    libuv_start_this_watcher = libuv.uv_prepare_start
    libuv_stop_this_watcher = libuv.uv_prepare_stop
    libuv_handle_type = 'uv_prepare_t *'

    def __init__(self, hub, ref=True):
        """
        Initialize the watcher

        :param hub: a Hub() instance
        """
        self._uv_handle = self._new_libuv_handle()
        self._cb = ffi.callback("void(*)(uv_prepare_t *, int)", self._run_callback)
        libuv.uv_prepare_init(hub._uv_ptr, self._uv_handle)
        Watcher.__init__(self, hub, ref = ref)

    @property
    def active(self):
        return self.callback is not None
