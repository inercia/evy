
import os
import sys
import traceback

from interface import libuv, ffi




def before_block(evloop, _, revents):
    pass  # XXX: how do I check for signals from pure python??



class Loop(object):
    """
    A main loop
    """

    error_handler = None

    def __init__(self, flags = None, default = True, ptr = 0):
        """
        Initialize a default loop

        :param flags: modifiers for the loop
        :type flags: integer
        :param default: default loop
        :type default: boolean
        :param ptr:
        :type ptr:
        """
        sys.stderr.write("*** using uv loop\n")
        self._signal_checker = ffi.new("uv_prepare_t *")
        self._signal_checker_cb = ffi.callback("void(*)(uv_loop_t *, uv_prepare_t *, int)", before_block)
        libuv.uv_prepare_init(self._signal_checker, self._signal_checker_cb)

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
        from watchers import Watcher
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
        from watchers import Poll
        return Poll(self, fd, events, ref)

    def timer(self, after, repeat=0.0, ref=True):
        from watchers import Timer
        return Timer(self, after, repeat, ref)

    def signal(self, signum, ref=True):
        from watchers import Signal
        return Signal(self, signum, ref)

    def idle(self, ref=True):
        from watchers import Idle
        return Idle(self, ref)

    def prepare(self, ref=True):
        from watchers import Prepare
        return Prepare(self, ref)

    def async(self, ref=True):
        from watchers import Async
        return Async(self, ref)

    def callback(self):
        from watchers import Callback
        return Callback(self)

    def run_callback(self, func, *args, **kw):
        from watchers import Callback
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

