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


from unittest import TestCase, main
import warnings

from evy import hubs
from evy.event import Event
from evy.green.threads import sleep, spawn, spawn_n, kill, spawn_after, spawn_after_local
from evy.green.threads import with_timeout, TimeoutError
from evy.support import greenlets as greenlet
from evy.io.convenience import listen, connect

from tests import LimitedTestCase
from test_hub import check_hub


warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('default', DeprecationWarning)



_g_results = []

def passthru (*args, **kw):
    _g_results.append((args, kw))
    return args, kw


def waiter (a):
    sleep(0.1)
    return a




class Asserts(object):
    def assert_dead (self, gt):
        if hasattr(gt, 'wait'):
            self.assertRaises(greenlet.GreenletExit, gt.wait)
        self.assert_(gt.dead)
        self.assert_(not gt)


class TestSpawn(LimitedTestCase, Asserts):
    def tearDown (self):
        global _g_results
        super(TestSpawn, self).tearDown()
        _g_results = []

    def test_simple (self):
        gt = spawn(passthru, 1, b = 2)
        self.assertEquals(gt.wait(), ((1,), {'b': 2}))
        self.assertEquals(_g_results, [((1,), {'b': 2})])

    def test_n (self):
        gt = spawn_n(passthru, 2, b = 3)
        self.assert_(not gt.dead)
        sleep(0)
        self.assert_(gt.dead)
        self.assertEquals(_g_results, [((2,), {'b': 3})])

    def test_kill (self):
        gt = spawn(passthru, 6)
        kill(gt)
        self.assert_dead(gt)
        sleep(0.001)
        self.assertEquals(_g_results, [])
        kill(gt)
        self.assert_dead(gt)

    def test_kill_meth (self):
        gt = spawn(passthru, 6)
        gt.kill()
        self.assert_dead(gt)
        sleep(0.001)
        self.assertEquals(_g_results, [])
        gt.kill()
        self.assert_dead(gt)

    def test_kill_n (self):
        gt = spawn_n(passthru, 7)
        kill(gt)
        self.assert_dead(gt)
        sleep(0.001)
        self.assertEquals(_g_results, [])
        kill(gt)
        self.assert_dead(gt)

    def test_link (self):
        results = []

        def link_func (g, *a, **kw):
            results.append(g)
            results.append(a)
            results.append(kw)

        gt = spawn(passthru, 5)
        gt.link(link_func, 4, b = 5)
        self.assertEquals(gt.wait(), ((5,), {}))
        self.assertEquals(results, [gt, (4,), {'b': 5}])

    def test_link_after_exited (self):
        results = []

        def link_func (g, *a, **kw):
            results.append(g)
            results.append(a)
            results.append(kw)

        gt = spawn(passthru, 5)
        self.assertEquals(gt.wait(), ((5,), {}))
        gt.link(link_func, 4, b = 5)
        self.assertEquals(results, [gt, (4,), {'b': 5}])


class TestSpawnAfter(LimitedTestCase, Asserts):
    def test_basic (self):
        gt = spawn_after(0.1, passthru, 20)
        self.assertEquals(gt.wait(), ((20,), {}))

    def test_cancel (self):
        gt = spawn_after(0.1, passthru, 21)
        gt.cancel()
        self.assert_dead(gt)

    def test_cancel_already_started (self):
        gt = spawn_after(0, waiter, 22)
        sleep(0)
        gt.cancel()
        self.assertEquals(gt.wait(), 22)

    def test_kill_already_started (self):
        gt = spawn_after(0, waiter, 22)
        sleep(0)
        gt.kill()
        self.assert_dead(gt)


class TestSpawnAfterLocal(LimitedTestCase, Asserts):
    def setUp (self):
        super(TestSpawnAfterLocal, self).setUp()
        self.lst = [1]

    def test_timer_fired (self):
        def func ():
            spawn_after_local(0.1, self.lst.pop)
            sleep(0.2)

        spawn(func)
        assert self.lst == [1], self.lst
        sleep(0.3)
        assert self.lst == [], self.lst

    def test_timer_cancelled_upon_greenlet_exit (self):
        def func ():
            spawn_after_local(0.1, self.lst.pop)

        spawn(func)
        assert self.lst == [1], self.lst
        sleep(0.2)
        assert self.lst == [1], self.lst

    def test_spawn_is_not_cancelled (self):
        def func ():
            spawn(self.lst.pop)
            # exiting immediatelly, but self.lst.pop must be called

        spawn(func)
        sleep(0.1)
        assert self.lst == [], self.lst



class TestGreenHub(TestCase):



    def test_001_trampoline_timeout (self):
        server_sock = listen(('127.0.0.1', 0))
        bound_port = server_sock.getsockname()[1]

        def server (sock):
            client, addr = sock.accept()
            sleep(0.1)

        server_evt = spawn(server, server_sock)
        sleep(0)
        
        try:
            desc = connect(('127.0.0.1', bound_port))
            hubs.trampoline(desc, read = True, write = False, timeout = 0.001)
        except TimeoutError:
            pass # test passed
        else:
            assert False, "Didn't timeout"

        server_evt.wait()
        check_hub()

    def test_timeout_cancel (self):
        server = listen(('0.0.0.0', 0))
        _, bound_port = server.getsockname()

        done = Event()

        def client_closer (sock):
            while True:
                (conn, addr) = sock.accept()
                conn.close()

        def go ():
            desc = connect(('127.0.0.1', bound_port))
            try:
                hubs.trampoline(desc, read = True, timeout = 0.1)
            except TimeoutError:
                assert False, "Timed out"

            server.close()
            desc.close()
            done.send()

        spawn_after_local(0, go)

        server_coro = spawn(client_closer, server)
        done.wait()
        kill(server_coro)

        check_hub()

    def test_killing_dormant (self):
        DELAY = 0.1
        state = []

        def test ():
            try:
                state.append('start')
                sleep(DELAY)
            except:
                state.append('except')
                # catching GreenletExit
                pass
                # when switching to hub, hub makes itself the parent of this greenlet,
            # thus after the function's done, the control will go to the parent
            sleep(0)
            state.append('finished')

        g = spawn(test)
        sleep(DELAY / 2)
        self.assertEquals(state, ['start'])
        kill(g)
        # will not get there, unless switching is explicitly scheduled by kill
        self.assertEquals(state, ['start', 'except'])
        sleep(DELAY)
        self.assertEquals(state, ['start', 'except', 'finished'])

    def test_nested_with_timeout (self):
        def func ():
            return with_timeout(0.2, sleep, 2, timeout_value = 1)

        self.assertRaises(TimeoutError, with_timeout, 0.1, func)


class Foo(object):
    pass
