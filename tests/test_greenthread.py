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

from tests import LimitedTestCase
from tests import skip_if_no_ssl

from evy import greenthread
from evy import hubs

from evy.support import greenlets as greenlet
from evy.greenthread import spawn
from evy.convenience import listen, connect



warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('default', DeprecationWarning)



_g_results = []

def passthru (*args, **kw):
    _g_results.append((args, kw))
    return args, kw


def waiter (a):
    greenthread.sleep(0.1)
    return a

def check_hub ():
    # Clear through the descriptor queue
    greenthread.sleep(0)
    greenthread.sleep(0)
    hub = hubs.get_hub()
    for nm in 'get_readers', 'get_writers':
        dct = getattr(hub, nm)()
        assert not dct, "hub.%s not empty: %s" % (nm, dct)
        # Stop the runloop (unless it's twistedhub which does not support that)
    if not getattr(hub, 'uses_twisted_reactor', None):
        hub.abort(True)
        assert not hub.running




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
        gt = greenthread.spawn(passthru, 1, b = 2)
        self.assertEquals(gt.wait(), ((1,), {'b': 2}))
        self.assertEquals(_g_results, [((1,), {'b': 2})])

    def test_n (self):
        gt = greenthread.spawn_n(passthru, 2, b = 3)
        self.assert_(not gt.dead)
        greenthread.sleep(0)
        self.assert_(gt.dead)
        self.assertEquals(_g_results, [((2,), {'b': 3})])

    def test_kill (self):
        gt = greenthread.spawn(passthru, 6)
        greenthread.kill(gt)
        self.assert_dead(gt)
        greenthread.sleep(0.001)
        self.assertEquals(_g_results, [])
        greenthread.kill(gt)
        self.assert_dead(gt)

    def test_kill_meth (self):
        gt = greenthread.spawn(passthru, 6)
        gt.kill()
        self.assert_dead(gt)
        greenthread.sleep(0.001)
        self.assertEquals(_g_results, [])
        gt.kill()
        self.assert_dead(gt)

    def test_kill_n (self):
        gt = greenthread.spawn_n(passthru, 7)
        greenthread.kill(gt)
        self.assert_dead(gt)
        greenthread.sleep(0.001)
        self.assertEquals(_g_results, [])
        greenthread.kill(gt)
        self.assert_dead(gt)

    def test_link (self):
        results = []

        def link_func (g, *a, **kw):
            results.append(g)
            results.append(a)
            results.append(kw)

        gt = greenthread.spawn(passthru, 5)
        gt.link(link_func, 4, b = 5)
        self.assertEquals(gt.wait(), ((5,), {}))
        self.assertEquals(results, [gt, (4,), {'b': 5}])

    def test_link_after_exited (self):
        results = []

        def link_func (g, *a, **kw):
            results.append(g)
            results.append(a)
            results.append(kw)

        gt = greenthread.spawn(passthru, 5)
        self.assertEquals(gt.wait(), ((5,), {}))
        gt.link(link_func, 4, b = 5)
        self.assertEquals(results, [gt, (4,), {'b': 5}])


class TestSpawnAfter(LimitedTestCase, Asserts):
    def test_basic (self):
        gt = greenthread.spawn_after(0.1, passthru, 20)
        self.assertEquals(gt.wait(), ((20,), {}))

    def test_cancel (self):
        gt = greenthread.spawn_after(0.1, passthru, 21)
        gt.cancel()
        self.assert_dead(gt)

    def test_cancel_already_started (self):
        gt = greenthread.spawn_after(0, waiter, 22)
        greenthread.sleep(0)
        gt.cancel()
        self.assertEquals(gt.wait(), 22)

    def test_kill_already_started (self):
        gt = greenthread.spawn_after(0, waiter, 22)
        greenthread.sleep(0)
        gt.kill()
        self.assert_dead(gt)


class TestSpawnAfterLocal(LimitedTestCase, Asserts):
    def setUp (self):
        super(TestSpawnAfterLocal, self).setUp()
        self.lst = [1]

    def test_timer_fired (self):
        def func ():
            greenthread.spawn_after_local(0.1, self.lst.pop)
            greenthread.sleep(0.2)

        greenthread.spawn(func)
        assert self.lst == [1], self.lst
        greenthread.sleep(0.3)
        assert self.lst == [], self.lst

    def test_timer_cancelled_upon_greenlet_exit (self):
        def func ():
            greenthread.spawn_after_local(0.1, self.lst.pop)

        greenthread.spawn(func)
        assert self.lst == [1], self.lst
        greenthread.sleep(0.2)
        assert self.lst == [1], self.lst

    def test_spawn_is_not_cancelled (self):
        def func ():
            greenthread.spawn(self.lst.pop)
            # exiting immediatelly, but self.lst.pop must be called

        greenthread.spawn(func)
        greenthread.sleep(0.1)
        assert self.lst == [], self.lst



class TestGreenHub(TestCase):


    def test_tcp_listener (self):
        socket = listen(('0.0.0.0', 0))
        assert socket.getsockname()[0] == '0.0.0.0'
        socket.close()

        check_hub()

    def test_connect_tcp (self):
        def accept_once (listenfd):
            try:
                conn, addr = listenfd.accept()
                fd = conn.makefile(mode = 'w')
                conn.close()
                fd.write('hello\n')
                fd.close()
            finally:
                listenfd.close()

        server = listen(('0.0.0.0', 0))
        greenthread.spawn(accept_once, server)

        client = connect(('127.0.0.1', server.getsockname()[1]))
        fd = client.makefile()
        client.close()
        assert fd.readline() == 'hello\n'

        assert fd.read() == ''
        fd.close()

        check_hub()

    def test_001_trampoline_timeout (self):
        server_sock = listen(('127.0.0.1', 0))
        bound_port = server_sock.getsockname()[1]

        def server (sock):
            client, addr = sock.accept()
            greenthread.sleep(0.1)

        server_evt = spawn(server, server_sock)
        greenthread.sleep(0)
        try:
            desc = connect(('127.0.0.1', bound_port))
            hubs.trampoline(desc, read = True, write = False, timeout = 0.001)
        except greenthread.TimeoutError:
            pass # test passed
        else:
            assert False, "Didn't timeout"

        server_evt.wait()
        check_hub()

    def test_timeout_cancel (self):
        server = listen(('0.0.0.0', 0))
        bound_port = server.getsockname()[1]

        done = [False]

        def client_closer (sock):
            while True:
                (conn, addr) = sock.accept()
                conn.close()

        def go ():
            desc = connect(('127.0.0.1', bound_port))
            try:
                hubs.trampoline(desc, read = True, timeout = 0.1)
            except greenthread.TimeoutError:
                assert False, "Timed out"

            server.close()
            desc.close()
            done[0] = True

        greenthread.spawn_after_local(0, go)

        server_coro = greenthread.spawn(client_closer, server)
        while not done[0]:
            greenthread.sleep(0)
        greenthread.kill(server_coro)

        check_hub()

    def test_killing_dormant (self):
        DELAY = 0.1
        state = []

        def test ():
            try:
                state.append('start')
                greenthread.sleep(DELAY)
            except:
                state.append('except')
                # catching GreenletExit
                pass
                # when switching to hub, hub makes itself the parent of this greenlet,
            # thus after the function's done, the control will go to the parent
            greenthread.sleep(0)
            state.append('finished')

        g = greenthread.spawn(test)
        greenthread.sleep(DELAY / 2)
        self.assertEquals(state, ['start'])
        greenthread.kill(g)
        # will not get there, unless switching is explicitly scheduled by kill
        self.assertEquals(state, ['start', 'except'])
        greenthread.sleep(DELAY)
        self.assertEquals(state, ['start', 'except', 'finished'])

    def test_nested_with_timeout (self):
        def func ():
            return greenthread.with_timeout(0.2, greenthread.sleep, 2, timeout_value = 1)

        self.assertRaises(greenthread.TimeoutError, greenthread.with_timeout, 0.1, func)


class Foo(object):
    pass
