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


import itertools

from evy import hubs

from evy.timeout import Timeout
from evy.support import greenlets as greenlet
from evy.event import Event
from evy.green.pools import GreenPool
from evy.green.threads import spawn, sleep


import tests

def passthru (a):
    sleep(0.01)
    return a


def passthru2 (a, b):
    sleep(0.01)
    return a, b


def raiser (exc):
    raise exc


class TestGreenPool(tests.LimitedTestCase):

    def test_spawn (self):
        p = GreenPool(4)
        waiters = []
        for i in xrange(10):
            waiters.append(p.spawn(passthru, i))
        results = [waiter.wait() for waiter in waiters]
        self.assertEquals(results, list(xrange(10)))

    def test_spawn_n (self):
        p = GreenPool(4)
        results_closure = []

        def do_something (a):
            sleep(0.01)
            results_closure.append(a)

        for i in xrange(10):
            p.spawn(do_something, i)
        p.waitall()
        self.assertEquals(sorted(results_closure), range(10))


    def test_multiple_coros (self):
        evt = Event()
        results = []

        def producer ():
            results.append('prod')
            evt.send()

        def consumer ():
            results.append('cons1')
            evt.wait()
            results.append('cons2')

        pool = GreenPool(2)
        done = pool.spawn(consumer)
        pool.spawn_n(producer)
        done.wait()
        self.assertEquals(['cons1', 'prod', 'cons2'], results)

    def test_timer_cancel (self):
        # this test verifies that local timers are not fired 
        # outside of the context of the spawn
        timer_fired = []

        def fire_timer ():
            timer_fired.append(True)

        def some_work ():
            hubs.get_hub().schedule_call_local(0, fire_timer)

        pool = GreenPool(2)
        worker = pool.spawn(some_work)
        worker.wait()
        sleep(0)
        sleep(0)
        self.assertEquals(timer_fired, [])

    def test_reentrant (self):
        pool = GreenPool(1)

        def reenter ():
            waiter = pool.spawn(lambda a: a, 'reenter')
            self.assertEqual('reenter', waiter.wait())

        outer_waiter = pool.spawn(reenter)
        outer_waiter.wait()

        evt = Event()

        def reenter_async ():
            pool.spawn_n(lambda a: a, 'reenter')
            evt.send('done')

        pool.spawn_n(reenter_async)
        self.assertEquals('done', evt.wait())

    def assert_pool_has_free (self, pool, num_free):
        self.assertEquals(pool.free(), num_free)

        def wait_long_time (e):
            e.wait()

        timer = Timeout(1)
        try:
            evt = Event()
            for x in xrange(num_free):
                pool.spawn(wait_long_time, evt)
                # if the pool has fewer free than we expect,
                # then we'll hit the timeout error
        finally:
            timer.cancel()

        # if the runtime error is not raised it means the pool had
        # some unexpected free items
        timer = Timeout(0, RuntimeError)
        try:
            self.assertRaises(RuntimeError, pool.spawn, wait_long_time, evt)
        finally:
            timer.cancel()

        # clean up by causing all the wait_long_time functions to return
        evt.send(None)
        sleep(0)
        sleep(0)

    def test_resize (self):
        pool = GreenPool(2)
        evt = Event()

        def wait_long_time (e):
            e.wait()

        pool.spawn(wait_long_time, evt)
        pool.spawn(wait_long_time, evt)
        self.assertEquals(pool.free(), 0)
        self.assertEquals(pool.running(), 2)
        self.assert_pool_has_free(pool, 0)

        # verify that the pool discards excess items put into it
        pool.resize(1)

        # cause the wait_long_time functions to return, which will
        # trigger puts to the pool
        evt.send(None)
        sleep(0)
        sleep(0)

        self.assertEquals(pool.free(), 1)
        self.assertEquals(pool.running(), 0)
        self.assert_pool_has_free(pool, 1)

        # resize larger and assert that there are more free items
        pool.resize(2)
        self.assertEquals(pool.free(), 2)
        self.assertEquals(pool.running(), 0)
        self.assert_pool_has_free(pool, 2)

    def test_pool_smash (self):
        """
        The premise is that a coroutine in a Pool tries to get a token out of a token pool but times out
        before getting the token.  We verify that neither pool is adversely affected by this situation.
        """
        from evy import pools

        pool = GreenPool(1)
        tp = pools.TokenPool(max_size = 1)
        token = tp.get()  # empty out the pool

        def do_receive (tp):
            _timer = Timeout(0, RuntimeError())
            try:
                t = tp.get()
                self.fail("Shouldn't have recieved anything from the pool")
            except RuntimeError:
                return 'timed out'
            else:
                _timer.cancel()

        # the spawn makes the token pool expect that coroutine, but then
        # immediately cuts bait
        e1 = pool.spawn(do_receive, tp)
        self.assertEquals(e1.wait(), 'timed out')

        # the pool can get some random item back
        def send_wakeup (tp):
            tp.put('wakeup')

        gt = spawn(send_wakeup, tp)

        # now we ask the pool to run something else, which should not
        # be affected by the previous send at all
        def resume ():
            return 'resumed'

        e2 = pool.spawn(resume)
        self.assertEquals(e2.wait(), 'resumed')

        # we should be able to get out the thing we put in there, too
        self.assertEquals(tp.get(), 'wakeup')
        gt.wait()

    def test_spawn_n_2 (self):
        p = GreenPool(2)
        self.assertEqual(p.free(), 2)
        r = []

        def foo (a):
            r.append(a)

        gt = p.spawn(foo, 1)
        self.assertEqual(p.free(), 1)
        gt.wait()
        self.assertEqual(r, [1])
        sleep(0)
        self.assertEqual(p.free(), 2)

        #Once the pool is exhausted, spawning forces a yield.
        p.spawn_n(foo, 2)
        self.assertEqual(1, p.free())
        self.assertEqual(r, [1])

        p.spawn_n(foo, 3)
        self.assertEqual(0, p.free())
        self.assertEqual(r, [1])

        p.spawn_n(foo, 4)
        self.assertEqual(set(r), set([1, 2, 3]))
        sleep(0)
        self.assertEqual(set(r), set([1, 2, 3, 4]))

    def test_exceptions (self):
        p = GreenPool(2)
        for m in (p.spawn, p.spawn_n):
            self.assert_pool_has_free(p, 2)
            m(raiser, RuntimeError())
            self.assert_pool_has_free(p, 1)
            p.waitall()
            self.assert_pool_has_free(p, 2)
            m(raiser, greenlet.GreenletExit)
            self.assert_pool_has_free(p, 1)
            p.waitall()
            self.assert_pool_has_free(p, 2)

    def test_imap (self):
        p = GreenPool(4)
        result_list = list(p.imap(passthru, xrange(10)))
        self.assertEquals(result_list, list(xrange(10)))

    def test_empty_imap (self):
        p = GreenPool(4)
        result_iter = p.imap(passthru, [])
        self.assertRaises(StopIteration, result_iter.next)

    def test_imap_nonefunc (self):
        p = GreenPool(4)
        result_list = list(p.imap(None, xrange(10)))
        self.assertEquals(result_list, [(x,) for x in xrange(10)])

    def test_imap_multi_args (self):
        p = GreenPool(4)
        result_list = list(p.imap(passthru2, xrange(10), xrange(10, 20)))
        self.assertEquals(result_list, list(itertools.izip(xrange(10), xrange(10, 20))))

    def test_imap_raises (self):
        """
        testing the case where the function raises an exception both that the caller sees that exception, and that the iterator
        continues to be usable to get the rest of the items
        """
        p = GreenPool(4)

        def raiser (item):
            if item == 1 or item == 7:
                raise RuntimeError("intentional error")
            else:
                return item

        it = p.imap(raiser, xrange(10))
        results = []
        while True:
            try:
                results.append(it.next())
            except RuntimeError:
                results.append('r')
            except StopIteration:
                break
        self.assertEquals(results, [0, 'r', 2, 3, 4, 5, 6, 'r', 8, 9])

    def test_starmap (self):
        p = GreenPool(4)
        result_list = list(p.starmap(passthru, [(x,) for x in xrange(10)]))
        self.assertEquals(result_list, range(10))

    def test_waitall_on_nothing (self):
        p = GreenPool()
        p.waitall()

    def test_recursive_waitall (self):
        p = GreenPool()
        gt = p.spawn(p.waitall)
        self.assertRaises(AssertionError, gt.wait)


    def test_execute_async (self):
        done = Event()

        def some_work ():
            done.send()

        pool = GreenPool(2)
        pool.spawn(some_work)
        done.wait()

    def test_execute (self):
        value = 'return value'

        def some_work ():
            return value

        pool = GreenPool(2)
        worker = pool.spawn(some_work)
        self.assertEqual(value, worker.wait())

    def test_waiting (self):
        pool = GreenPool(1)
        done = Event()

        def consume ():
            done.wait()

        def waiter (pool):
            evt = pool.spawn(consume)
            evt.wait()

        waiters = []
        waiters.append(spawn(waiter, pool))
        sleep(0)
        self.assertEqual(pool.waiting(), 0)
        waiters.append(spawn(waiter, pool))
        sleep(0)
        self.assertEqual(pool.waiting(), 1)
        waiters.append(spawn(waiter, pool))
        sleep(0)
        self.assertEqual(pool.waiting(), 2)
        done.send(None)
        for w in waiters:
            w.wait()
        self.assertEqual(pool.waiting(), 0)

    def test_multiple_coros (self):
        evt = Event()
        results = []

        def producer ():
            results.append('prod')
            evt.send()

        def consumer ():
            results.append('cons1')
            evt.wait()
            results.append('cons2')

        pool = GreenPool(2)
        done = pool.spawn(consumer)
        pool.spawn(producer)
        done.wait()
        self.assertEquals(sorted(['cons1', 'prod', 'cons2']), sorted(results))

    def test_timer_cancel (self):
        # this test verifies that local timers are not fired
        # outside of the context of the spawn method
        timer_fired = []

        def fire_timer ():
            timer_fired.append(True)

        def some_work ():
            hubs.get_hub().schedule_call_local(0, fire_timer)

        pool = GreenPool(2)
        worker = pool.spawn(some_work)
        worker.wait()
        sleep(0)
        self.assertEquals(timer_fired, [])

    def test_reentrant (self):
        pool = GreenPool(1)

        def reenter ():
            waiter = pool.spawn(lambda a: a, 'reenter')
            self.assertEqual('reenter', waiter.wait())

        outer_waiter = pool.spawn(reenter)
        outer_waiter.wait()

        evt = Event()

        def reenter_async ():
            pool.spawn(lambda a: a, 'reenter')
            evt.send('done')

        pool.spawn(reenter_async)
        evt.wait()



    def test_resize (self):
        pool = GreenPool(2)
        evt = Event()

        def wait_long_time (e):
            e.wait()

        pool.spawn(wait_long_time, evt)
        pool.spawn(wait_long_time, evt)
        self.assertEquals(pool.free(), 0)
        self.assert_pool_has_free(pool, 0)

        # verify that the pool discards excess items put into it
        pool.resize(1)

        # cause the wait_long_time functions to return, which will
        # trigger puts to the pool
        evt.send(None)
        sleep(0)
        sleep(0)

        self.assertEquals(pool.free(), 1)
        self.assert_pool_has_free(pool, 1)

        # resize larger and assert that there are more free items
        pool.resize(2)
        self.assertEquals(pool.free(), 2)
        self.assert_pool_has_free(pool, 2)

    def test_stderr_raising (self):
        # testing that really egregious errors in the error handling code
        # (that prints tracebacks to stderr) don't cause the pool to lose
        # any members
        import sys

        pool = GreenPool(1)

        def crash (*args, **kw):
            raise RuntimeError("Whoa")

        class FakeFile(object):
            write = crash

        # we're going to do this by causing the traceback.print_exc in
        # safe_apply to raise an exception and thus exit _main_loop
        normal_err = sys.stderr
        try:
            sys.stderr = FakeFile()
            waiter = pool.spawn(crash)
            self.assertRaises(RuntimeError, waiter.wait)
            # the pool should have something free at this point since the
            # waiter returned
            # GreenPool change: if an exception is raised during execution of a link,
            # the rest of the links are scheduled to be executed on the next hub iteration
            # this introduces a delay in updating pool.sem which makes pool.free() report 0
            # therefore, sleep:
            sleep(0)
            self.assertEqual(pool.free(), 1)
            # shouldn't block when trying to get
            t = Timeout(0.1)
            try:
                pool.spawn(sleep, 1)
            finally:
                t.cancel()
        finally:
            sys.stderr = normal_err


    def test_pool_smash (self):
        # The premise is that a coroutine in a Pool tries to get a token out
        # of a token pool but times out before getting the token.  We verify
        # that neither pool is adversely affected by this situation.
        from evy import pools

        pool = GreenPool(1)
        tp = pools.TokenPool(max_size = 1)
        token = tp.get()  # empty pool

        def do_receive (tp):
            Timeout(0, RuntimeError())
            try:
                t = tp.get()
                self.fail("Shouldn't have recieved anything from the pool")
            except RuntimeError:
                return 'timed out'

        # the execute makes the token pool expect that coroutine, but then
        # immediately cuts bait
        e1 = pool.spawn(do_receive, tp)
        self.assertEquals(e1.wait(), 'timed out')

        # the pool can get some random item back
        def send_wakeup (tp):
            tp.put('wakeup')

        spawn(send_wakeup, tp)

        # now we ask the pool to run something else, which should not
        # be affected by the previous send at all
        def resume ():
            return 'resumed'

        e2 = pool.spawn(resume)
        self.assertEquals(e2.wait(), 'resumed')

        # we should be able to get out the thing we put in there, too
        self.assertEquals(tp.get(), 'wakeup')


    def test_execute_async (self):
        p = GreenPool(2)
        self.assertEqual(p.free(), 2)
        r = []

        def foo (a):
            r.append(a)

        evt = p.spawn(foo, 1)
        self.assertEqual(p.free(), 1)
        evt.wait()
        self.assertEqual(r, [1])
        sleep(0)
        self.assertEqual(p.free(), 2)

        #Once the pool is exhausted, calling an execute forces a yield.

        p.spawn(foo, 2)
        self.assertEqual(1, p.free())
        self.assertEqual(r, [1])

        p.spawn(foo, 3)
        self.assertEqual(0, p.free())
        self.assertEqual(r, [1])

        p.spawn(foo, 4)
        self.assertEqual(sorted(r), sorted([1, 2, 3]))
        sleep(0)
        self.assertEqual(sorted(r), sorted([1, 2, 3, 4]))

    def test_execute (self):
        p = GreenPool()
        evt = p.spawn(lambda a: ('foo', a), 1)
        self.assertEqual(evt.wait(), ('foo', 1))

    def test_with_intpool (self):
        from evy import pools

        class IntPool(pools.Pool):
            def create (self):
                self.current_integer = getattr(self, 'current_integer', 0) + 1
                return self.current_integer

        def subtest (intpool_size, pool_size, num_executes):
            def run (int_pool):
                token = int_pool.get()
                sleep(0.0001)
                int_pool.put(token)
                return token

            int_pool = IntPool(intpool_size)
            pool = GreenPool(pool_size)
            for ix in xrange(num_executes):
                pool.spawn(run, int_pool)
            pool.waitall()

        subtest(4, 7, 7)
        subtest(50, 75, 100)
        for isize in (20, 30, 40, 50):
            for psize in (25, 35, 50):
                subtest(isize, psize, psize)

