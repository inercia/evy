from __future__ import absolute_import
import sys, os, traceback, signal as signalmodule

__all__ = ['supported_backends',
           'recommended_backends',
           'embeddable_backends',
           'time',
           'loop']



################################################################################################################

import signal
import time

from evy.support import greenlets as greenlet

from evy.hubs import hub

from evy.uv import libuv
from evy.uv.loop import Loop
from evy.uv.watchers import Signal, Poll, Timer


class Hub(hub.BaseHub):
    """
    A UV hub
    """

    def __init__(self, clock = time.time):
        """

        :param clock:
        :type clock:
        :return:
        :rtype:
        """
        super(Hub, self).__init__(clock)
        self.interrupted = False
        self._uv_loop = Loop()

    def add (self, evtype, fileno, cb):
        listener = super(Hub, self).add(evtype, fileno, cb)

        events = 0
        if evtype & hub.READ:    events |= libuv.UV_READABLE
        if evtype & hub.WRITE:   events |= libuv.UV_WRITABLE

        if events != 0:
            evt = Poll(self._uv_loop, fileno, events)
            evt.start()

        return listener

    def abort(self):
        super(Hub, self).abort()
        print "abort(): TODO"

    def signal_received(self, signal):
        # can't do more than set this flag here because the pyevent callback
        # mechanism swallows exceptions raised here, so we have to raise in
        # the 'main' greenlet (in wait()) to kill the program
        self.interrupted = True
        print "signal_received(): TODO"

    def wait(self, seconds=None):
        # this timeout will cause us to return from the dispatch() call
        # when we want to
        timer = Timer(self._uv_loop, seconds)
        timer.start()

        try:
            status = self._uv_loop.loop()
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

    def add_timer(self, timer):
        # store the pyevent timer object so that we can cancel later
        eventtimer = Timer(self._uv_loop, timer.seconds)
        timer.impltimer = eventtimer
        eventtimer.start()
        self.track_timer(timer)

    def timer_finished(self, timer):
        try:
            timer.impltimer.stop()
            del timer.impltimer
        # XXX might this raise other errors?
        except (AttributeError, TypeError):
            pass
        finally:
            super(Hub, self).timer_finished(timer)

    def timer_canceled(self, timer):
        """ Cancels the underlying libevent timer. """
        try:
            timer.impltimer.stop()
            del timer.impltimer
        except (AttributeError, TypeError):
            pass
        finally:
            super(Hub, self).timer_canceled(timer)