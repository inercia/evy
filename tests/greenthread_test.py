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


from tests import LimitedTestCase
from evy import greenthread
from evy.support import greenlets as greenlet

_g_results = []

def passthru (*args, **kw):
    _g_results.append((args, kw))
    return args, kw


def waiter (a):
    greenthread.sleep(0.1)
    return a


class Asserts(object):
    def assert_dead (self, gt):
        if hasattr(gt, 'wait'):
            self.assertRaises(greenlet.GreenletExit, gt.wait)
        self.assert_(gt.dead)
        self.assert_(not gt)


class Spawn(LimitedTestCase, Asserts):
    def tearDown (self):
        global _g_results
        super(Spawn, self).tearDown()
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


class SpawnAfter(LimitedTestCase, Asserts):
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


class SpawnAfterLocal(LimitedTestCase, Asserts):
    def setUp (self):
        super(SpawnAfterLocal, self).setUp()
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
