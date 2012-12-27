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

from tests import LimitedTestCase, main, silence_warnings, skipped

from evy import event
from evy.green.threads import spawn, sleep, waitall
from evy.queue import Queue
from evy.event import Event
from evy.timeout import Timeout, with_timeout



def do_bail (q):
    Timeout(0, RuntimeError())
    try:
        result = q.get()
        return result
    except RuntimeError:
        return 'timed out'


class TestQueue(LimitedTestCase):

    @silence_warnings
    def test_send_first (self):
        q = Queue()
        q.put('hi')
        self.assertEquals(q.get(), 'hi')

    @silence_warnings
    def test_send_last (self):
        q = Queue()

        def waiter (q):
            timer = Timeout(0.2)
            self.assertEquals(q.join(), 'hi2')
            timer.cancel()

        spawn(waiter, q)
        sleep(0)
        sleep(0)
        q.put('hi2')

    @silence_warnings
    def test_max_size (self):
        q = Queue(2)
        results = []

        def putter (q):
            q.put('a')
            results.append('a')
            q.put('b')
            results.append('b')
            q.put('c')
            results.append('c')

        spawn(putter, q)
        sleep(0)
        self.assertEquals(results, ['a', 'b'])
        self.assertEquals(q.get(), 'a')
        sleep(0)
        self.assertEquals(results, ['a', 'b', 'c'])
        self.assertEquals(q.get(), 'b')
        self.assertEquals(q.get(), 'c')

    @silence_warnings
    def test_zero_max_size (self):
        q = Queue(0)

        def sender (evt, q):
            q.put('hi')
            evt.send('done')

        def receiver (evt, q):
            x = q.join()
            evt.send(x)

        e1 = Event()
        e2 = Event()

        spawn(sender, e1, q)
        sleep(0)
        self.assert_(not e1.ready())
        spawn(receiver, e2, q)
        self.assertEquals(e2.wait(), 'hi')
        self.assertEquals(e1.wait(), 'done')

    @skipped
    @silence_warnings
    def test_multiple_waiters (self):

        self.reset_timeout(100000000)

        # tests that multiple waiters get their results back
        q = Queue()

        sendings = ['1', '2', '3', '4']
        gts = [spawn(q.join) for x in sendings]

        sleep(0.01) # get 'em all waiting

        q.put(sendings[0])
        q.put(sendings[1])
        q.put(sendings[2])
        q.put(sendings[3])

        results = waitall(*gts)
        self.assertEquals(sorted(results), sorted(sendings))

    @silence_warnings
    def test_waiters_that_cancel (self):
        q = Queue()

        def do_receive (q, evt):
            Timeout(0, RuntimeError())
            try:
                result = q.join()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')

        evt = Event()
        spawn(do_receive, q, evt)
        self.assertEquals(evt.wait(), 'timed out')

        q.put('hi')
        self.assertEquals(q.get(), 'hi')

    @silence_warnings
    def test_senders_that_die (self):
        q = Queue()

        def do_send (q):
            q.put('sent')

        spawn(do_send, q)
        self.assertEquals(q.join(), 'sent')

    @silence_warnings
    def test_two_waiters_one_dies (self):
        def waiter (q, evt):
            evt.send(q.join())

        def do_receive (q, evt):
            Timeout(0, RuntimeError())
            try:
                result = q.get()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')

        q = Queue()
        dying_evt = Event()
        waiting_evt = Event()
        spawn(do_receive, q, dying_evt)
        spawn(waiter, q, waiting_evt)
        sleep(0)
        q.put('hi')
        self.assertEquals(dying_evt.wait(), 'timed out')
        self.assertEquals(waiting_evt.wait(), 'hi')

    @silence_warnings
    def test_two_bogus_waiters (self):
        def do_receive (q, evt):
            Timeout(0, RuntimeError())
            try:
                result = q.join()
                evt.send(result)
            except RuntimeError:
                evt.send('timed out')

        q = Queue()
        e1 = Event()
        e2 = Event()
        spawn(do_receive, q, e1)
        spawn(do_receive, q, e2)
        sleep(0)
        q.put('sent')
        self.assertEquals(e1.wait(), 'timed out')
        self.assertEquals(e2.wait(), 'timed out')
        self.assertEquals(q.get(), 'sent')

    @silence_warnings
    def test_waiting (self):
        def do_wait (q, evt):
            result = q.join()
            evt.send(result)

        q = Queue()
        e1 = Event()
        spawn(do_wait, q, e1)
        sleep(0)
        self.assertEquals(1, q.join())
        q.put('hi')
        sleep(0)
        self.assertEquals(0, q.join())
        self.assertEquals('hi', e1.wait())
        self.assertEquals(0, q.join())

    def test_send_first (self):
        q = Queue()
        q.put('hi')
        self.assertEquals(q.get(), 'hi')

    def test_send_last (self):
        q = Queue()

        def waiter (q):
            self.assertEquals(q.get(), 'hi2')

        gt = spawn(with_timeout, 0.1, waiter, q)
        sleep(0)
        sleep(0)
        q.put('hi2')
        gt.wait()

    def test_max_size (self):
        q = Queue(2)
        results = []

        def putter (q):
            q.put('a')
            results.append('a')
            q.put('b')
            results.append('b')
            q.put('c')
            results.append('c')

        gt = spawn(putter, q)
        sleep(0)
        self.assertEquals(results, ['a', 'b'])
        self.assertEquals(q.get(), 'a')
        sleep(0)
        self.assertEquals(results, ['a', 'b', 'c'])
        self.assertEquals(q.get(), 'b')
        self.assertEquals(q.get(), 'c')
        gt.wait()

    def test_zero_max_size (self):
        q = Queue(0)

        def sender (evt, q):
            q.put('hi')
            evt.send('done')

        def receiver (q):
            x = q.get()
            return x

        evt = event.Event()
        gt = spawn(sender, evt, q)
        sleep(0)
        self.assert_(not evt.ready())
        gt2 = spawn(receiver, q)
        self.assertEquals(gt2.wait(), 'hi')
        self.assertEquals(evt.wait(), 'done')
        gt.wait()

    def test_resize_up (self):
        q = Queue(0)

        def sender (evt, q):
            q.put('hi')
            evt.send('done')

        evt = event.Event()
        gt = spawn(sender, evt, q)
        sleep(0)
        self.assert_(not evt.ready())
        q.resize(1)
        sleep(0)
        self.assert_(evt.ready())
        gt.wait()

    def test_resize_down (self):
        size = 5
        q = Queue(5)

        for i in range(5):
            q.put(i)

        self.assertEquals(list(q.queue), range(5))
        q.resize(1)
        sleep(0)
        self.assertEquals(list(q.queue), range(5))

    def test_resize_to_Unlimited (self):
        q = Queue(0)

        def sender (evt, q):
            q.put('hi')
            evt.send('done')

        evt = event.Event()
        gt = spawn(sender, evt, q)
        sleep()
        self.assertFalse(evt.ready())
        q.resize(None)
        sleep()
        self.assertTrue(evt.ready())
        gt.wait()

    def test_waiters_that_cancel (self):
        q = Queue()

        gt = spawn(do_bail, q)
        self.assertEquals(gt.wait(), 'timed out')

        q.put('hi')
        self.assertEquals(q.get(), 'hi')

    def test_getting_before_sending (self):
        q = Queue()
        gt = spawn(q.put, 'sent')
        self.assertEquals(q.get(), 'sent')
        gt.wait()

    def test_two_waiters_one_dies (self):
        def waiter (q):
            return q.get()

        q = Queue()
        dying = spawn(do_bail, q)
        waiting = spawn(waiter, q)
        sleep(0)
        q.put('hi')
        self.assertEquals(dying.wait(), 'timed out')
        self.assertEquals(waiting.wait(), 'hi')

    def test_two_bogus_waiters (self):
        q = Queue()
        gt1 = spawn(do_bail, q)
        gt2 = spawn(do_bail, q)
        sleep(0)
        q.put('sent')
        self.assertEquals(gt1.wait(), 'timed out')
        self.assertEquals(gt2.wait(), 'timed out')
        self.assertEquals(q.get(), 'sent')

    def test_waiting (self):
        q = Queue()
        gt1 = spawn(q.get)
        sleep(0)
        self.assertEquals(1, q.getting())
        q.put('hi')
        sleep(0)
        self.assertEquals(0, q.getting())
        self.assertEquals('hi', gt1.wait())
        self.assertEquals(0, q.getting())

    def test_channel_send (self):
        channel = Queue(0)
        events = []

        def another_greenlet ():
            events.append(channel.get())
            events.append(channel.get())

        gt = spawn(another_greenlet)

        events.append('sending')
        channel.put('hello')
        events.append('sent hello')
        channel.put('world')
        events.append('sent world')

        self.assertEqual(['sending', 'hello', 'sent hello', 'world', 'sent world'], events)


    def test_channel_wait (self):
        channel = Queue(0)
        events = []

        def another_greenlet ():
            events.append('sending hello')
            channel.put('hello')
            events.append('sending world')
            channel.put('world')
            events.append('sent world')

        gt = spawn(another_greenlet)

        events.append('waiting')
        events.append(channel.get())
        events.append(channel.get())

        self.assertEqual(['waiting', 'sending hello', 'hello', 'sending world', 'world'], events)
        sleep(0)
        self.assertEqual(
            ['waiting', 'sending hello', 'hello', 'sending world', 'world', 'sent world'], events)

    def test_channel_waiters (self):
        c = Queue(0)
        w1 = spawn(c.get)
        w2 = spawn(c.get)
        w3 = spawn(c.get)
        sleep(0)
        self.assertEquals(c.getting(), 3)
        s1 = spawn(c.put, 1)
        s2 = spawn(c.put, 2)
        s3 = spawn(c.put, 3)

        s1.wait()
        s2.wait()
        s3.wait()
        self.assertEquals(c.getting(), 0)
        # NOTE: we don't guarantee that waiters are served in order
        results = sorted([w1.wait(), w2.wait(), w3.wait()])
        self.assertEquals(results, [1, 2, 3])

    def test_channel_sender_timing_out (self):
        from evy import queue

        c = Queue(0)
        self.assertRaises(queue.Full, c.put, "hi", timeout = 0.001)
        self.assertRaises(queue.Empty, c.get_nowait)

    def test_task_done (self):
        from evy import queue
        from evy.tools import debug
        
        channel = queue.Queue(0)
        X = object()
        gt = spawn(channel.put, X)
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
        q = Queue(1)
        hub.run_callback(store_result, result, q.put_nowait, 2)
        hub.run_callback(store_result, result, q.put_nowait, 3)
        sleep(0)
        sleep(0)
        assert len(result) == 2, result
        assert result[0] == None, result
        assert isinstance(result[1], queue.Full), result

    def test_get_nowait_simple (self):
        from evy import hubs, queue

        hub = hubs.get_hub()
        result = []
        q = queue.Queue(1)
        q.put(4)
        hub.run_callback(store_result, result, q.get_nowait)
        hub.run_callback(store_result, result, q.get_nowait)
        sleep(0)
        assert len(result) == 2, result
        assert result[0] == 4, result
        assert isinstance(result[1], queue.Empty), result

    # get_nowait must work from the mainloop
    def test_get_nowait_unlock (self):
        from evy import hubs, queue

        hub = hubs.get_hub()
        result = []
        q = queue.Queue(0)
        p = spawn(q.put, 5)
        assert q.empty(), q
        assert q.full(), q
        sleep(0)
        assert q.empty(), q
        assert q.full(), q
        hub.run_callback(store_result, result, q.get_nowait)
        sleep(0)
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
        p = spawn(q.get)
        assert q.empty(), q
        assert q.full(), q
        sleep(0)
        assert q.empty(), q
        assert q.full(), q
        hub.run_callback(store_result, result, q.put_nowait, 10)
        # TODO ready method on greenthread
        #assert not p.ready(), p
        sleep(0)
        assert result == [None], result
        # TODO ready method
        # assert p.ready(), p
        assert q.full(), q
        assert q.empty(), q




if __name__ == '__main__':
    main()
