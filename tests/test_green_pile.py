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




from evy.green.pools import GreenPool, GreenPile
from evy.green.threads import spawn, sleep
from evy.timeout import Timeout

import tests

def passthru (a):
    sleep(0.01)
    return a


def passthru2 (a, b):
    sleep(0.01)
    return a, b


def raiser (exc):
    raise exc



class TestGreenPile(tests.LimitedTestCase):
    def test_pile (self):
        p = GreenPile(4)
        for i in xrange(10):
            p.spawn(passthru, i)
        result_list = list(p)
        self.assertEquals(result_list, list(xrange(10)))

    def test_pile_spawn_times_out (self):
        p = GreenPile(4)
        for i in xrange(4):
            p.spawn(passthru, i)
            # now it should be full and this should time out
        Timeout(0)
        self.assertRaises(Timeout, p.spawn, passthru, "time out")
        # verify that the spawn breakage didn't interrupt the sequence
        # and terminates properly
        for i in xrange(4, 10):
            p.spawn(passthru, i)
        self.assertEquals(list(p), list(xrange(10)))

    def test_constructing_from_pool (self):
        pool = GreenPool(2)
        pile1 = GreenPile(pool)
        pile2 = GreenPile(pool)

        def bunch_of_work (pile, unique):
            for i in xrange(10):
                pile.spawn(passthru, i + unique)

        spawn(bunch_of_work, pile1, 0)
        spawn(bunch_of_work, pile2, 100)
        sleep(0)
        self.assertEquals(list(pile2), list(xrange(100, 110)))
        self.assertEquals(list(pile1), list(xrange(10)))

