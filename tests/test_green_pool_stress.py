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


import gc
import random

from evy.green.pools import GreenPile, GreenPool
from evy.green.threads import spawn, sleep

import tests




class StressException(Exception):
    pass

r = random.Random(0)



def pressure (arg):
    while r.random() < 0.5:
        sleep(r.random() * 0.001)
    if r.random() < 0.8:
        return arg
    else:
        raise StressException(arg)


def passthru (arg):
    while r.random() < 0.5:
        sleep(r.random() * 0.001)
    return arg


class Stress(tests.LimitedTestCase):
    # tests will take extra-long
    TEST_TIMEOUT = 60

    def spawn_order_check (self, concurrency):
        # checks that piles are strictly ordered
        p = GreenPile(concurrency)

        def makework (count, unique):
            for i in xrange(count):
                token = (unique, i)
                p.spawn(pressure, token)

        iters = 1000
        spawn(makework, iters, 1)
        spawn(makework, iters, 2)
        spawn(makework, iters, 3)
        p.spawn(pressure, (0, 0))
        latest = [-1] * 4
        received = 0
        it = iter(p)
        while True:
            try:
                i = it.next()
            except StressException, exc:
                i = exc.args[0]
            except StopIteration:
                break
            received += 1
            if received % 5 == 0:
                sleep(0.0001)
            unique, order = i
            self.assert_(latest[unique] < order)
            latest[unique] = order
        for l in latest[1:]:
            self.assertEquals(l, iters - 1)

    def test_ordering_5 (self):
        self.spawn_order_check(5)

    def test_ordering_50 (self):
        self.spawn_order_check(50)

    def imap_memory_check (self, concurrency):
        # checks that imap is strictly
        # ordered and consumes a constant amount of memory
        p = GreenPool(concurrency)
        count = 1000
        it = p.imap(passthru, xrange(count))
        latest = -1
        while True:
            try:
                i = it.next()
            except StopIteration:
                break

            if latest == -1:
                gc.collect()
                initial_obj_count = len(gc.get_objects())
            self.assert_(i > latest)
            latest = i
            if latest % 5 == 0:
                sleep(0.001)
            if latest % 10 == 0:
                gc.collect()
                objs_created = len(gc.get_objects()) - initial_obj_count
                self.assert_(objs_created < 25 * concurrency, objs_created)
            # make sure we got to the end
        self.assertEquals(latest, count - 1)

    #@tests.skip_unless(os.environ.get('RUN_STRESS_TESTS') == 'YES')
    def test_imap_50 (self):
        self.imap_memory_check(50)

    def test_imap_500 (self):
        self.imap_memory_check(500)

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

            int_pool = IntPool(max_size = intpool_size)
            pool = GreenPool(pool_size)
            for ix in xrange(num_executes):
                pool.spawn(run, int_pool)
            pool.waitall()

        subtest(4, 7, 7)
        subtest(50, 75, 100)
        for isize in (10, 20, 30, 40, 50):
            for psize in (5, 25, 35, 50):
                subtest(isize, psize, psize)
