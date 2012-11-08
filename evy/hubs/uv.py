from __future__ import absolute_import
import sys, os, traceback, signal as signalmodule

from evy.uv import libuv, ffi

__all__ = ['get_version',
           'get_header_version',
           'supported_backends',
           'recommended_backends',
           'embeddable_backends',
           'time',
           'loop']



def get_header_version():
    return 'libuv-%d.%02d' % (libuv.UV_VERSION_MAJOR, libuv.UV_VERSION_MINOR)


####################################################################################################


class Loop(object):
    """
    A main loop
    """

    error_handler = None

    def __init__(self, flags=None, default=True, ptr=0):
        sys.stderr.write("*** using uv loop\n")
        self._signal_checker = ffi.new("uv_prepare_t *")
        self._signal_checker_cb = ffi.callback("void(*)(uv_loop_t *, uv_prepare_t *, int)", before_block)
        libuv.uv_prepare_init(self._signal_checker, self._signal_checker_cb)

        # #ifdef _WIN32
        #         libuv.uv_timer_init(&self._periodic_signal_checker, <void*>gevent_periodic_signal_check, 0.3, 0.3)
        # #endif

        if ptr:
            assert ffi.typeof(ptr) is ffi.typeof("uv_loop_t *")
            self._ptr = ptr
        else:
            if _default_loop_destroyed:
                default = False
            if default:
                self._ptr = libuv.uv_default_loop()
                if not self._ptr:
                    raise SystemError("uv_default_loop() failed")
                libuv.uv_prepare_start(self._ptr, self._signal_checker)
                libuv.uv_unref(self._ptr)

                # if sys.platform == "win32":
                #     libuv.uv_timer_start(self._ptr, &self._periodic_signal_checker)
                #     libuv.uv_unref(self._ptr)

            else:
                self._ptr = libuv.uv_loop_new()
                if not self._ptr:
                    raise SystemError("uv_loop_new() failed")
                
            #if default or __SYSERR_CALLBACK is None:
            #    set_syserr_cb(self._handle_syserr)

    def _stop_signal_checker(self):
        if libuv.uv_is_active(self._signal_checker):
            libuv.uv_ref(self._ptr)
            libuv.uv_prepare_stop(self._ptr, self._signal_checker)
        # #ifdef _WIN32
        #         if libuv.uv_is_active(&self._periodic_signal_checker):
        #             libuv.uv_ref(self._ptr)
        #             libuv.uv_timer_stop(self._ptr, &self._periodic_signal_checker)
        # #endif

    def destroy(self):
        global _default_loop_destroyed
        if self._ptr:
            self._stop_signal_checker()
            #if __SYSERR_CALLBACK == self._handle_syserr:
            #    set_syserr_cb(None)
            if libuv.uv_is_default_loop(self._ptr):
                _default_loop_destroyed = True
            libuv.uv_loop_destroy(self._ptr)
            self._ptr = ffi.NULL

    @property
    def ptr(self):
        return self._ptr

    @property
    def WatcherType(self):
        return Watcher

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
        # note: Hub sets its own error handler so this is not used by gevent
        # this is here to make core.loop usable without the rest of gevent
        traceback.print_exception(type, value, tb)
        #libuv.uv_break(self._ptr, libuv.EVBREAK_ONE)
        raise NotImplementedError()

    def run(self, once=False):
        if once:
            libuv.uv_run_once(self._ptr)
        else:
            libuv.uv_run(self._ptr)

    def ref(self):
        libuv.uv_ref(self._ptr)

    def unref(self):
        libuv.uv_unref(self._ptr)

    def now(self):
        return libuv.uv_now(self._ptr)

    def XXX__repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), self._format())

    @property
    def default_loop(self):
        return libuv.uv_default_loop()

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
        fd = self._ptr.backend_fd
        if fd >= 0:
            return fd


####################################################################################################


class Watcher(object):
    """
    An general watcher
    """
    libuv_start_this_watcher = None
    libuv_stop_this_watcher = None

    _callback = None
    loop = None
    args = None
    _flags = 0

    def __init__(self, _loop, ref=True):
        assert isinstance(_loop, Loop)
        assert self.libuv_stop_this_watcher is not None
        self.loop = _loop
        if ref:
            self._flags = 0
        else:
            self._flags = 4

    def _run_callback(self, loop, c_watcher, revents):
        try:
            self.callback(*self.args)
        except:
            try:
                self.loop.handle_error(self, *sys.exc_info())
            finally:
                if revents & (libuv.UV_READABLE | libuv.UV_WRITABLE):
                    # /* poll watcher: not stopping it may cause the failing callback to be called repeatedly */
                    try:
                        self.stop()
                    except:
                        self.loop.handle_error(self, *sys.exc_info())
                    return

        # callbacks' self.active differs from uv_is_active(...) at
        # this point. don't use it!
        if not libuv.uv_is_active(c_watcher):
            self.stop()

    def _libuv_unref(self):
        if self._flags & 6 == 4:
            libuv.uv_unref(self.loop._ptr)
            self._flags |= 2

    def _python_incref(self):
        if not self._flags & 1:
            # Py_INCREF(<PyObjectPtr>self)
            self._flags |= 1

    def _get_ref(self):
        return False if self._flags & 4 else True

    def _set_ref(self, value):
        if value:
            if not self._flags & 4:
                return  # ref is already True
            if self._flags & 2:  # uv_unref was called, undo
                libuv.uv_ref(self.loop._ptr)
            self._flags &= ~6  # do not want unref, no outstanding unref
        else:
            if self._flags & 4:
                return  # ref is already False
            self._flags |= 4
            if not self._flags & 2 and libuv.uv_is_active(self._watcher):
                libuv.uv_unref(self.loop._ptr)
                self._flags |= 2

    ref = property(_get_ref, _set_ref)

    def _get_callback(self):
        return self._callback

    def _set_callback(self, callback):
        assert callable(callback)
        self._callback = callback
    callback = property(_get_callback, _set_callback)

    def start(self, callback, *args):
        self.callback = callback
        self.args = args
        self._libuv_unref()
        self.libuv_start_this_watcher(self.loop._ptr, self._watcher)
        self._python_incref()

    def stop(self):
        if self._flags & 2:
            libuv.uv_ref(self.loop._ptr)
            self._flags &= ~2
        self.libuv_stop_this_watcher(self.loop._ptr, self._watcher)
        self._callback = None
        self.args = None
        if self._flags & 1:
            # Py_DECREF(<PyObjectPtr>self)
            self._flags &= ~1

    def feed(self, revents, callback, *args):
        self.callback = callback
        self.args = args
        if self._flags & 6 == 4:
            libuv.uv_unref(self.loop._ptr)
            self._flags |= 2
        libuv.uv_feed_event(self.loop._ptr, self._watcher, revents)
        if not self._flags & 1:
            # Py_INCREF(<PyObjectPtr>self)
            self._flags |= 1

    @property
    def active(self):
        return True if libuv.uv_is_active(self._watcher) else False

    @property
    def pending(self):
        return True if libuv.uv_is_pending(self._watcher) else False



class Poll(Watcher):
    """
    This watcher is used to watch file descriptors for readability and writability, similar to the
    purpose of poll(2).

    The purpose is to enable integrating external libraries that rely on the event loop to signal
    it about the socket status changes, like c-ares or libssh2. Using Poll for any other other
    purpose is not recommended; uv_tcp_t, uv_udp_t, etc. provide an implementation that is much
    faster and more scalable than what can be achieved with uv_poll_t, especially on Windows.

    It is possible that Poll occasionally signals that a file descriptor is readable or writable
    even when it isn't. The user should therefore always be prepared to handle EAGAIN or equivalent
    when it attempts to read from or write to the fd.

    It is not okay to have multiple active Poll watchers for the same socket. This can cause
    libuv to busyloop or otherwise malfunction.

    The user should not close a file descriptor while it is being polled by an active Poll watcher.
    This can cause the poll watcher to report an error, but it might also start polling another socket.
    However the fd can be safely closed immediately after a call to uv_poll_stop() or uv_close().

    On windows only sockets can be polled with uv_poll. On unix any file
    descriptor that would be accepted by poll(2) can be used with uv_poll.
    """
    libuv_start_this_watcher = libuv.uv_poll_start
    libuv_stop_this_watcher = libuv.uv_poll_stop

    def __init__(self, loop, fd, events, ref=True):
        if fd < 0:
            raise ValueError('fd must be non-negative: %r' % fd)

        if events & ~(libuv.UV_READABLE | libuv.UV_WRITABLE):
            raise ValueError('illegal event mask: %r' % events)

        self._watcher = ffi.new("uv_poll_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_poll_t *, int)", self._run_callback)

        libuv.uv_poll_init(self._watcher, self._cb, fd, events)
        Watcher.__init__(self, loop, ref=ref)

    def _get_fd(self):
        return self._watcher.fd

    def _set_fd(self, fd):
        if libuv.uv_is_active(self._watcher):
            raise AttributeError("'poll' watcher attribute 'fd' is read-only while watcher is active")
        libuv.uv_poll_init(self._watcher, self._cb, fd, self._watcher.events)

    fd = property(_get_fd, _set_fd)

    def _get_events(self):
        return self._watcher.fd

    def _set_events(self, events):
        if libuv.uv_is_active(self._watcher):
            raise AttributeError("'poll' watcher attribute 'events' is read-only while watcher is active")
        libuv.uv_poll_init(self._watcher, self._cb, self._watcher.fd, events)

    events = property(_get_events, _set_events)

    def _format(self):
        return ' fd=%s events=%s' % (self.fd, self.events_str)



class Timer(Watcher):
    """
    Start a timer. `timeout` and `repeat` are in milliseconds.

    If timeout is zero, the callback fires on the next tick of the event loop.

    If repeat is non-zero, the callback fires first after timeout milliseconds and then repeatedly
    after repeat milliseconds.

    timeout and repeat are signed integers but that will change in a future version of libuv. Don't
    pass in negative values, you'll get a nasty surprise when that change becomes effective.
    """
    libuv_start_this_watcher = libuv.uv_timer_start
    libuv_stop_this_watcher = libuv.uv_timer_stop

    def __init__(self, loop, after=0.0, repeat=0.0, ref=True):
        if repeat < 0.0:
            raise ValueError("repeat must be positive or zero: %r" % repeat)

        self._watcher = ffi.new("uv_timer_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_timer_t *, int)", self._run_callback)

        libuv.uv_timer_init(self._watcher, self._cb, after, repeat)
        Watcher.__init__(self, loop, ref=ref)

    def start(self, callback, *args, **kw):
        update = kw.get("update", True)
        self.callback = callback
        self.args = args

        self._libuv_unref()  # LIBEV_UNREF

        if update:
            libuv.uv_update_time(self.loop._ptr)

        libuv.uv_timer_start(self.loop._ptr, self._watcher)

        self._python_incref()  # PYTHON_INCREF

    @property
    def at(self):
        return self._watcher.at

    def again(self, callback, *args, **kw):
        update = kw.get("update", True)
        self.callback = callback
        self.args = args
        self._libuv_unref()
        if update:
            libuv.uv_now_update(self.loop._ptr)
        libuv.uv_timer_again(self.loop._ptr, self._watcher)
        self._python_incref()


class Signal(Watcher):
    """
    UNIX signal handling on a per-event loop basis. The implementation is not
    ultra efficient so don't go creating a million event loops with a million
    signal watchers.

    Some signal support is available on Windows:

      SIGINT is normally delivered when the user presses CTRL+C. However, like
      on Unix, it is not generated when terminal raw mode is enabled.

      SIGBREAK is delivered when the user pressed CTRL+BREAK.

      SIGHUP is generated when the user closes the console window. On SIGHUP the
      program is given approximately 10 seconds to perform cleanup. After that
      Windows will unconditionally terminate it.

      SIGWINCH is raised whenever libuv detects that the console has been
      resized. SIGWINCH is emulated by libuv when the program uses an uv_tty_t
      handle to write to the console. SIGWINCH may not always be delivered in a
      timely manner; libuv will only detect size changes when the cursor is
      being moved. When a readable uv_tty_handle is used in raw mode, resizing
      the console buffer will also trigger a SIGWINCH signal.

    Watchers for other signals can be successfully created, but these signals
    are never generated. These signals are: SIGILL, SIGABRT, SIGFPE, SIGSEGV,
    SIGTERM and SIGKILL.

    Note that calls to raise() or abort() to programmatically raise a signal are
    not detected by libuv; these will not trigger a signal watcher.

    """
    libuv_start_this_watcher = libuv.uv_signal_start
    libuv_stop_this_watcher = libuv.uv_signal_stop

    def __init__(self, loop, signalnum, ref=True):
        if signalnum < 1 or signalnum >= signalmodule.NSIG:
            raise ValueError('illegal signal number: %r' % signalnum)
            # still possible to crash on one of libuv's asserts:
        # 1) "libuv: uv_signal_start called with illegal signal number"
        #    EV_NSIG might be different from signal.NSIG on some platforms
        # 2) "libuv: a signal must not be attached to two different loops"
        #    we probably could check that in LIBEV_EMBED mode, but not in general

        self._watcher = ffi.new("uv_signal_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_signal_t *, int)", self._run_callback)

        libuv.uv_signal_init(self._watcher, self._cb, signalnum)
        Watcher.__init__(self, loop, ref=ref)


class Idle(Watcher):
    """
    Every active idle handle gets its callback called repeatedly until it is stopped. This happens
    after all other types of callbacks are processed. When there are multiple "idle" handles active,
    their callbacks are called in turn.
    """
    libuv_start_this_watcher = libuv.uv_idle_start
    libuv_stop_this_watcher = libuv.uv_idle_stop

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_idle_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_idle_t *, int)", self._run_callback)
        libuv.uv_idle_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)


class Prepare(Watcher):
    """
    Every active prepare handle gets its callback called exactly once per loop iteration, just before
    the system blocks to wait for completed i/o.
    """
    libuv_start_this_watcher = libuv.uv_prepare_start
    libuv_stop_this_watcher = libuv.uv_prepare_stop

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_prepare_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_prepare_t *, int)", self._run_callback)
        libuv.uv_prepare_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)


class Async(Watcher):
    """
    An Async wakes up the event loop and calls the async handle's callback.
    There is no guarantee that every send() call leads to exactly one invocation of the
    callback; the only guarantee is that the callback function is called at least once after the
    call send(). Unlike all other libuv functions, send() can be called from
    another thread.
    """
    libuv_start_this_watcher = None
    libuv_stop_this_watcher = None

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_async_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_async_t *, int)", self._run_callback)
        libuv.uv_async_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)

    def send(self):
        libuv.uv_async_send(self.loop._ptr, self._watcher)

    @property
    def pending(self):
        return True if libuv.uv_async_pending(self._watcher) else False



class Callback(Watcher):
    """
    Pseudo-watcher used to execute a callback in the loop as soon as possible.
    """

    # does not matter which type we actually use, since we are going
    # to feed() events, not start watchers

    libuv_start_this_watcher = libuv.uv_prepare_start
    libuv_stop_this_watcher = libuv.uv_prepare_stop

    def __init__(self, loop, ref=True):
        self._watcher = ffi.new("uv_prepare_t *")
        self._cb = ffi.callback("void(*)(uv_loop_t *, uv_prepare_t *, int)", self._run_callback)
        libuv.uv_prepare_init(self._watcher, self._cb)
        Watcher.__init__(self, loop, ref=ref)

    def start(self, callback, *args):
        self.callback = callback
        self.args = args
        libuv.uv_feed_event(self.loop._ptr, self._watcher, libuv.EV_CUSTOM)
        self._python_incref()

    @property
    def active(self):
        return self.callback is not None


