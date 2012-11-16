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



from evy import hubs
from evy.support import greenlets as greenlet

__all__ = ['Event']

class NOT_USED:
    def __repr__ (self):
        return 'NOT_USED'

NOT_USED = NOT_USED()

class Event(object):
    """
    An abstraction where an arbitrary number of coroutines can wait for one event from another.

    Events are similar to a Queue that can only hold one item, but differ in two important ways:

    1. calling :meth:`send` never unschedules the current greenthread
    2. :meth:`send` can only be called once; create a new event to send again.

    They are good for communicating results between coroutines, and are the basis for how
    :meth:`GreenThread.wait() <evy.greenthread.GreenThread.wait>` is implemented.

    >>> from evy import event
    >>> import evy
    >>> evt = event.Event()
    >>> def baz(b):
    ...     evt.send(b + 1)
    ...
    >>> _ = evy.spawn_n(baz, 3)
    >>> evt.wait()
    4
    """
    _result = None
    _exc = None

    def __init__ (self):
        self._waiters = set()
        self.reset()

    def __str__ (self):
        params = (self.__class__.__name__, hex(id(self)),
                  self._result, self._exc, len(self._waiters))
        return '<%s at %s result=%r _exc=%r _waiters[%d]>' % params

    def reset (self):
        # this is kind of a misfeature and doesn't work perfectly well,
        # it's better to create a new event rather than reset an old one
        # removing documentation so that we don't get new use cases for it
        assert self._result is not NOT_USED, 'Trying to re-reset() a fresh event.'
        self._result = NOT_USED
        self._exc = None

    def ready (self):
        """
        Return true if the :meth:`wait` call will return immediately.
        Used to avoid waiting for things that might take a while to time out.
        For example, you can put a bunch of events into a list, and then visit
        them all repeatedly, calling :meth:`ready` until one returns ``True``,
        and then you can :meth:`wait` on that one.
        """
        return self._result is not NOT_USED

    def has_exception (self):
        return self._exc is not None

    def has_result (self):
        return self._result is not NOT_USED and self._exc is None

    def poll (self, notready = None):
        if self.ready():
            return self.wait()
        return notready

    # QQQ make it return tuple (type, value, tb) instead of raising
    # because
    # 1) "poll" does not imply raising
    # 2) it's better not to screw up caller's sys.exc_info() by default
    #    (e.g. if caller wants to calls the function in except or finally)
    def poll_exception (self, notready = None):
        if self.has_exception():
            return self.wait()
        return notready

    def poll_result (self, notready = None):
        if self.has_result():
            return self.wait()
        return notready

    def wait (self):
        """
        Wait until another coroutine calls :meth:`send`.
        Returns the value the other coroutine passed to
        :meth:`send`.

        >>> from evy import event
        >>> import evy
        >>> evt = event.Event()
        >>> def wait_on():
        ...    retval = evt.wait()
        ...    print "waited for", retval
        >>> _ = evy.spawn(wait_on)
        >>> evt.send('result')
        >>> evy.sleep(0)
        waited for result

        Returns immediately if the event has already
        occured.

        >>> evt.wait()
        'result'
        """
        current = greenlet.getcurrent()
        if self._result is NOT_USED:
            self._waiters.add(current)
            try:
                return hubs.get_hub().switch()
            finally:
                self._waiters.discard(current)
        if self._exc is not None:
            current.throw(*self._exc)
        return self._result

    def send (self, result = None, exc = None):
        """
        Makes arrangements for the waiters to be woken with the
        result and then returns immediately to the parent.

        >>> from evy import event
        >>> import evy
        >>> evt = event.Event()
        >>> def waiter():
        ...     print 'about to wait'
        ...     result = evt.wait()
        ...     print 'waited for', result
        >>> _ = evy.spawn(waiter)
        >>> evy.sleep(0)
        about to wait
        >>> evt.send('a')
        >>> evy.sleep(0)
        waited for a

        It is an error to call :meth:`send` multiple times on the same event.

        >>> evt.send('whoops')
        Traceback (most recent call last):
        ...
        AssertionError: Trying to re-send() an already-triggered event.

        Use :meth:`reset` between :meth:`send` s to reuse an event object.
        """
        assert self._result is NOT_USED, 'Trying to re-send() an already-triggered event.'
        self._result = result
        if exc is not None and not isinstance(exc, tuple):
            exc = (exc, )
        self._exc = exc
        hub = hubs.get_hub()
        for waiter in self._waiters:
            hub.schedule_call_global(
                0, self._do_send, self._result, self._exc, waiter)

    def _do_send (self, result, exc, waiter):
        if waiter in self._waiters:
            if exc is None:
                waiter.switch(result)
            else:
                waiter.throw(*exc)

    def send_exception (self, *args):
        """
        Same as :meth:`send`, but sends an exception to waiters.
        
        The arguments to send_exception are the same as the arguments
        to ``raise``.  If a single exception object is passed in, it
        will be re-raised when :meth:`wait` is called, generating a
        new stacktrace.  
        
           >>> from evy import event
           >>> evt = event.Event()
           >>> evt.send_exception(RuntimeError())
           >>> evt.wait()
           Traceback (most recent call last):
             File "<stdin>", line 1, in <module>
             File "evy/event.py", line 120, in wait
               current.throw(*self._exc)
           RuntimeError
        
        If it's important to preserve the entire original stack trace,
        you must pass in the entire :func:`sys.exc_info` tuple.

           >>> import sys
           >>> evt = event.Event()
           >>> try:
           ...     raise RuntimeError()
           ... except RuntimeError:
           ...     evt.send_exception(*sys.exc_info())
           ... 
           >>> evt.wait()
           Traceback (most recent call last):
             File "<stdin>", line 1, in <module>
             File "evy/event.py", line 120, in wait
               current.throw(*self._exc)
             File "<stdin>", line 2, in <module>
           RuntimeError
           
        Note that doing so stores a traceback object directly on the
        Event object, which may cause reference cycles. See the
        :func:`sys.exc_info` documentation.
        """
        # the arguments and the same as for greenlet.throw
        return self.send(None, args)



class metaphore(object):
    """
    This is sort of an inverse semaphore: a counter that starts at 0 and
    waits only if nonzero. It's used to implement a "wait for all" scenario.

    >>> from evy import event
    >>> count = event.metaphore()
    >>> count.wait()
    >>> def decrementer(count, id):
    ...     print "%s decrementing" % id
    ...     count.dec()
    ...
    >>> _ = evy.spawn(decrementer, count, 'A')
    >>> _ = evy.spawn(decrementer, count, 'B')
    >>> count.inc(2)
    >>> count.wait()
    A decrementing
    B decrementing
    """

    def __init__ (self):
        self.counter = 0
        self.event = Event()
        # send() right away, else we'd wait on the default 0 count!
        self.event.send()

    def inc (self, by = 1):
        """
        Increment our counter. If this transitions the counter from zero to
        nonzero, make any subsequent :meth:`wait` call wait.
        """
        assert by > 0
        self.counter += by
        if self.counter == by:
            # If we just incremented self.counter by 'by', and the new count
            # equals 'by', then the old value of self.counter was 0.
            # Transitioning from 0 to a nonzero value means wait() must
            # actually wait.
            self.event.reset()

    def dec (self, by = 1):
        """
        Decrement our counter. If this transitions the counter from nonzero
        to zero, a current or subsequent wait() call need no longer wait.
        """
        assert by > 0
        self.counter -= by
        if self.counter <= 0:
            # Don't leave self.counter < 0, that will screw things up in
            # future calls.
            self.counter = 0
            # Transitioning from nonzero to 0 means wait() need no longer wait.
            self.event.send()

    def wait (self):
        """
        Suspend the caller only if our count is nonzero. In that case,
        resume the caller once the count decrements to zero again.
        """
        self.event.wait()

