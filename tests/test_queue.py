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

from unittest import main

from tests import LimitedTestCase, main, silence_warnings

import evy
from evy import event
from evy.greenthread import spawn, sleep
from evy.queue import Queue, LifoQueue
from evy.event import Event




def do_bail (q):
    evy.Timeout(0, RuntimeError())
    try:
        result = q.get()
        return result
    except RuntimeError:
        return 'timed out'


class TestQueue(LimitedTestCase):
    def test_send_first (self):
        q = evy.Queue()
        q.put('hi')
        self.assertEquals(q.get(), 'hi')

    def test_send_last (self):
        q = evy.Queue()

        def waiter (q):
            self.assertEquals(q.get(), 'hi2')

        gt = evy.spawn(evy.with_timeout, 0.1, waiter, q)
        evy.sleep(0)
        evy.sleep(0)
        q.put('hi2')
        gt.wait()

    def test_max_size (self):
        q = evy.Queue(2)
        results = []

        def putter (q):
            q.put('a')
            results.append('a')
            q.put('b')
            results.append('b')
            q.put('c')
            results.append('c')

        gt = evy.spawn(putter, q)
        evy.sleep(0)
        self.assertEquals(results, ['a', 'b'])
        self.assertEquals(q.get(), 'a')
        evy.sleep(0)
        self.assertEquals(results, ['a', 'b', 'c'])
        self.assertEquals(q.get(), 'b')
        self.assertEquals(q.get(), 'c')
        gt.wait()

    def test_zero_max_size (self):
        q = evy.Queue(0)

        def sender (evt, q):
            q.put('hi')
            evt.send('done')

        def receiver (q):
            x = q.get()
            return x

        evt = event.Event()
        gt = evy.spawn(sender, evt, q)
        evy.sleep(0)
        self.assert_(not evt.ready())
        gt2 = evy.spawn(receiver, q)
        self.assertEquals(gt2.wait(), 'hi')
        self.assertEquals(evt.wait(), 'done')
        gt.wait()

    def test_resize_up (self):
        q = evy.Queue(0)

        def sender (evt, q):
            q.put('hi')
            evt.send('done')

        evt = event.Event()
        gt = evy.spawn(sender, evt, q)
        evy.sleep(0)
        self.assert_(not evt.ready())
        q.resize(1)
        evy.sleep(0)
        self.assert_(evt.ready())
        gt.wait()

    def test_resize_down (self):
        size = 5
        q = evy.Queue(5)

        for i in range(5):
            q.put(i)

        self.assertEquals(list(q.queue), range(5))
        q.resize(1)
        evy.sleep(0)
        self.assertEquals(list(q.queue), range(5))

    def test_resize_to_Unlimited (self):
        q = evy.Queue(0)

        def sender (evt, q):
            q.put('hi')
            evt.send('done')

        evt = event.Event()
        gt = evy.spawn(sender, evt, q)
        evy.sleep()
        self.assertFalse(evt.ready())
        q.resize(None)
        evy.sleep()
        self.assertTrue(evt.ready())
        gt.wait()

    def test_multiple_waiters (self):
        # tests that multiple waiters get their results back
        q = evy.Queue()

        sendings = ['1', '2', '3', '4']
        gts = [evy.spawn(q.get)
               for x in sendings]

        evy.sleep(0.01) # get 'em all waiting

        q.put(sendings[0])
        q.put(sendings[1])
        q.put(sendings[2])
        q.put(sendings[3])
        results = set()
        for i, gt in enumerate(gts):
            results.add(gt.wait())
        self.assertEquals(results, set(sendings))

    def test_waiters_that_cancel (self):
        q = evy.Queue()

        gt = evy.spawn(do_bail, q)
        self.assertEquals(gt.wait(), 'timed out')

        q.put('hi')
        self.assertEquals(q.get(), 'hi')

    def test_getting_before_sending (self):
        q = evy.Queue()
        gt = evy.spawn(q.put, 'sent')
        self.assertEquals(q.get(), 'sent')
        gt.wait()

    def test_two_waiters_one_dies (self):
        def waiter (q):
            return q.get()

        q = evy.Queue()
        dying = evy.spawn(do_bail, q)
        waiting = evy.spawn(waiter, q)
        evy.sleep(0)
        q.put('hi')
        self.assertEquals(dying.wait(), 'timed out')
        self.assertEquals(waiting.wait(), 'hi')

    def test_two_bogus_waiters (self):
        q = evy.Queue()
        gt1 = evy.spawn(do_bail, q)
        gt2 = evy.spawn(do_bail, q)
        evy.sleep(0)
        q.put('sent')
        self.assertEquals(gt1.wait(), 'timed out')
        self.assertEquals(gt2.wait(), 'timed out')
        self.assertEquals(q.get(), 'sent')

    def test_waiting (self):
        q = evy.Queue()
        gt1 = evy.spawn(q.get)
        evy.sleep(0)
        self.assertEquals(1, q.getting())
        q.put('hi')
        evy.sleep(0)
        self.assertEquals(0, q.getting())
        self.assertEquals('hi', gt1.wait())
        self.assertEquals(0, q.getting())

    def test_channel_send (self):
        channel = evy.Queue(0)
        events = []

        def another_greenlet ():
            events.append(channel.get())
            events.append(channel.get())

        gt = evy.spawn(another_greenlet)

        events.append('sending')
        channel.put('hello')
        events.append('sent hello')
        channel.put('world')
        events.append('sent world')

        self.assertEqual(['sending', 'hello', 'sent hello', 'world', 'sent world'], events)


    def test_channel_wait (self):
        channel = evy.Queue(0)
        events = []

        def another_greenlet ():
            events.append('sending hello')
            channel.put('hello')
            events.append('sending world')
            channel.put('world')
            events.append('sent world')

        gt = evy.spawn(another_greenlet)

        events.append('waiting')
        events.append(channel.get())
        events.append(channel.get())

        self.assertEqual(['waiting', 'sending hello', 'hello', 'sending world', 'world'], events)
        evy.sleep(0)
        self.assertEqual(
            ['waiting', 'sending hello', 'hello', 'sending world', 'world', 'sent world'], events)

    def test_channel_waiters (self):
        c = evy.Queue(0)
        w1 = evy.spawn(c.get)
        w2 = evy.spawn(c.get)
        w3 = evy.spawn(c.get)
        evy.sleep(0)
        self.assertEquals(c.getting(), 3)
        s1 = evy.spawn(c.put, 1)
        s2 = evy.spawn(c.put, 2)
        s3 = evy.spawn(c.put, 3)

        s1.wait()
        s2.wait()
        s3.wait()
        self.assertEquals(c.getting(), 0)
        # NOTE: we don't guarantee that waiters are served in order
        results = sorted([w1.wait(), w2.wait(), w3.wait()])
        self.assertEquals(results, [1, 2, 3])

    def test_channel_sender_timing_out (self):
        from evy import queue

        c = evy.Queue(0)
        self.assertRaises(queue.Full, c.put, "hi", timeout = 0.001)
        self.assertRaises(queue.Empty, c.get_nowait)

    def test_task_done (self):
        from evy import queue, debug

        channel = queue.Queue(0)
        X = object()
        gt = evy.spawn(channel.put, X)
        result = channel.get()
        assert result is X, (result, X)
        assert channel.unfinished_tasks == 1, channel.unfinished_tasks
        channel.task_done()
        assert channel.unfinished_tasks == 0, channel.unfinished_tasks
        gt.wait()


def store_result (result, func, *args):
    try:
        result.append(func(*args))
    except Exception, exc:
        result.append(exc)


class TestNoWait(LimitedTestCase):
    def test_put_nowait_simple (self):
        from evy import hubs, queue

        hub = hubs.get_hub()
        result = []
        q = evy.Queue(1)
        hub.schedule_call_global(0, store_result, result, q.put_nowait, 2)
        hub.schedule_call_global(0, store_result, result, q.put_nowait, 3)
        evy.sleep(0)
        evy.sleep(0)
        assert len(result) == 2, result
        assert result[0] == None, result
        assert isinstance(result[1], queue.Full), result

    def test_get_nowait_simple (self):
        from evy import hubs, queue

        hub = hubs.get_hub()
        result = []
        q = queue.Queue(1)
        q.put(4)
        hub.schedule_call_global(0, store_result, result, q.get_nowait)
        hub.schedule_call_global(0, store_result, result, q.get_nowait)
        evy.sleep(0)
        assert len(result) == 2, result
        assert result[0] == 4, result
        assert isinstance(result[1], queue.Empty), result

    # get_nowait must work from the mainloop
    def test_get_nowait_unlock (self):
        from evy import hubs, queue

        hub = hubs.get_hub()
        result = []
        q = queue.Queue(0)
        p = evy.spawn(q.put, 5)
        assert q.empty(), q
        assert q.full(), q
        evy.sleep(0)
        assert q.empty(), q
        assert q.full(), q
        hub.schedule_call_global(0, store_result, result, q.get_nowait)
        evy.sleep(0)
        assert q.empty(), q
        assert q.full(), q
        assert result == [5], result
        # TODO add ready to greenthread
        #assert p.ready(), p
        assert p.dead, p
        assert q.empty(), q

    # put_nowait must work from the mainloop
    def test_put_nowait_unlock (self):
        from evy import hubs, queue

        hub = hubs.get_hub()
        result = []
        q = queue.Queue(0)
        p = evy.spawn(q.get)
        assert q.empty(), q
        assert q.full(), q
        evy.sleep(0)
        assert q.empty(), q
        assert q.full(), q
        hub.schedule_call_global(0, store_result, result, q.put_nowait, 10)
        # TODO ready method on greenthread
        #assert not p.ready(), p
        evy.sleep(0)
        assert result == [None], result
        # TODO ready method
        # assert p.ready(), p
        assert q.full(), q
        assert q.empty(), q




class TestQueue(LimitedTestCase):
    @silence_warnings
    def test_send_first (self):
        q = Queue()
        q.send('hi')
        self.assertEquals(q.wait(), 'hi')

    @silence_warnings
    def test_send_exception_first (self):
        q = Queue()
        q.send(exc = RuntimeError())
        self.assertRaises(RuntimeError, q.wait)

    @silence_warnings
    def test_send_last (self):
        q = Queue()

        def waiter (q):
            timer = evy.Timeout(0.1)
            self.assertEquals(q.wait(), 'hi2')
            timer.cancel()

        spawn(waiter, q)
        sleep(0)
        sleep(0)
        q.send('hi2')

    @silence_warnings
    def test_max_size (self):
        q = Queue(2)
        results = []

        def putter (q):
            q.send('a')
            results.append('a')
            q.send('b')
            results.append('b')
            q.send('c')
            results.append('c')

        spawn(putter, q)
        sleep(0)
        self.assertEquals(results, ['a', 'b'])
        self.assertEquals(q.wait(), 'a')
        sleep(0)
        self.assertEquals(results, ['a', 'b', 'c'])
        self.assertEquals(q.wait(), 'b')
        self.assertEquals(q.wait(), 'c')

    @silence_warnings
    def test_zero_max_size (self):
        q = Queue(0)

        def sender (evt, q):
            q.send('hi')
            evt.send('done')

        def receiver (evt, q):
            x = q.wait()
            evt.send(x)

        e1 = Event()
        e2 = Event()

        spawn(sender, e1, q)
        sleep(0)
        self.assert_(not e1.ready())
        spawn(receiver, e2, q)
        self.assertEquals(e2.wait(), 'hi')
        self.assertEquals(e1.wait(), 'done')

    @silence_warnings
    def test_multiple_waiters (self):
        # tests that multiple waiters get their results back
        q = Queue()

        sendings = ['1', '2', '3', '4']
        gts = [evy.spawn(q.wait)
               for x in sendings]

        evy.sleep(0.01) # get 'em all waiting

        q.send(sendings[0])
        q.send(sendings[1])
        q.send(sendings[2])
        q.send(sendings[3])
        results = set()
        for i, gt in enumerate(gts):
            results.add(gt.wait())
        self.assertEquals(results, set(sendings))

    @silence_warnings
    def test_waiters_that_cancel (self):
        q = Queue()

        def do_receive (q, evt):
            evy.Timeout(0, RuntimeError())
            try:
                result = q.wait()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')


        evt = Event()
        spawn(do_receive, q, evt)
        self.assertEquals(evt.wait(), 'timed out')

        q.send('hi')
        self.assertEquals(q.wait(), 'hi')

    @silence_warnings
    def test_senders_that_die (self):
        q = Queue()

        def do_send (q):
            q.send('sent')

        spawn(do_send, q)
        self.assertEquals(q.wait(), 'sent')

    @silence_warnings
    def test_two_waiters_one_dies (self):
        def waiter (q, evt):
            evt.send(q.wait())

        def do_receive (q, evt):
            evy.Timeout(0, RuntimeError())
            try:
                result = q.wait()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')

        q = Queue()
        dying_evt = Event()
        waiting_evt = Event()
        spawn(do_receive, q, dying_evt)
        spawn(waiter, q, waiting_evt)
        sleep(0)
        q.send('hi')
        self.assertEquals(dying_evt.wait(), 'timed out')
        self.assertEquals(waiting_evt.wait(), 'hi')

    @silence_warnings
    def test_two_bogus_waiters (self):
        def do_receive (q, evt):
            evy.Timeout(0, RuntimeError())
            try:
                result = q.wait()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')

        q = Queue()
        e1 = Event()
        e2 = Event()
        spawn(do_receive, q, e1)
        spawn(do_receive, q, e2)
        sleep(0)
        q.send('sent')
        self.assertEquals(e1.wait(), 'timed out')
        self.assertEquals(e2.wait(), 'timed out')
        self.assertEquals(q.wait(), 'sent')

    @silence_warnings
    def test_waiting (self):
        def do_wait (q, evt):
            result = q.wait()
            evt.send(result)

        q = Queue()
        e1 = Event()
        spawn(do_wait, q, e1)
        sleep(0)
        self.assertEquals(1, q.waiting())
        q.send('hi')
        sleep(0)
        self.assertEquals(0, q.waiting())
        self.assertEquals('hi', e1.wait())
        self.assertEquals(0, q.waiting())


class TestChannel(LimitedTestCase):
    @silence_warnings
    def test_send (self):
        sleep(0.1)
        channel = Queue(0)

        events = []

        def another_greenlet ():
            events.append(channel.wait())
            events.append(channel.wait())

        spawn(another_greenlet)

        events.append('sending')
        channel.send('hello')
        events.append('sent hello')
        channel.send('world')
        events.append('sent world')

        self.assertEqual(['sending', 'hello', 'sent hello', 'world', 'sent world'], events)


    @silence_warnings
    def test_wait (self):
        sleep(0.1)
        channel = Queue(0)
        events = []

        def another_greenlet ():
            events.append('sending hello')
            channel.send('hello')
            events.append('sending world')
            channel.send('world')
            events.append('sent world')

        spawn(another_greenlet)

        events.append('waiting')
        events.append(channel.wait())
        events.append(channel.wait())

        self.assertEqual(['waiting', 'sending hello', 'hello', 'sending world', 'world'], events)
        sleep(0)
        self.assertEqual(
            ['waiting', 'sending hello', 'hello', 'sending world', 'world', 'sent world'], events)

    @silence_warnings
    def test_waiters (self):
        c = LifoQueue()
        w1 = evy.spawn(c.wait)
        w2 = evy.spawn(c.wait)
        w3 = evy.spawn(c.wait)
        sleep(0)
        self.assertEquals(c.waiting(), 3)
        s1 = evy.spawn(c.send, 1)
        s2 = evy.spawn(c.send, 2)
        s3 = evy.spawn(c.send, 3)
        sleep(0)  # this gets all the sends into a waiting state
        self.assertEquals(c.waiting(), 0)

        s1.wait()
        s2.wait()
        s3.wait()
        # NOTE: we don't guarantee that waiters are served in order
        results = sorted([w1.wait(), w2.wait(), w3.wait()])
        self.assertEquals(results, [1, 2, 3])

if __name__ == '__main__':
    main()
