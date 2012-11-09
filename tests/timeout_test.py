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


import unittest

from tests import LimitedTestCase

from evy import timeout
from evy import greenthread

DELAY = 0.01

class TestDirectRaise(LimitedTestCase):
    def test_direct_raise_class (self):
        try:
            raise timeout.Timeout
        except timeout.Timeout, t:
            assert not t.pending, repr(t)

    def test_direct_raise_instance (self):
        tm = timeout.Timeout()
        try:
            raise tm
        except timeout.Timeout, t:
            assert tm is t, (tm, t)
            assert not t.pending, repr(t)

    def test_repr (self):
        # just verify these don't crash
        tm = timeout.Timeout(1)
        greenthread.sleep(0)
        repr(tm)
        str(tm)
        tm.cancel()
        tm = timeout.Timeout(None, RuntimeError)
        repr(tm)
        str(tm)
        tm = timeout.Timeout(None, False)
        repr(tm)
        str(tm)


class TestWithTimeout(LimitedTestCase):
    def test_with_timeout (self):
        self.assertRaises(timeout.Timeout, timeout.with_timeout, DELAY, greenthread.sleep,
                          DELAY * 10)
        X = object()
        r = timeout.with_timeout(DELAY, greenthread.sleep, DELAY * 10, timeout_value = X)
        self.assert_(r is X, (r, X))
        r = timeout.with_timeout(DELAY * 10, greenthread.sleep,
                                 DELAY, timeout_value = X)
        self.assert_(r is None, r)


    def test_with_outer_timer (self):
        def longer_timeout ():
            # this should not catch the outer timeout's exception
            return timeout.with_timeout(DELAY * 10,
                                        greenthread.sleep, DELAY * 20,
                                        timeout_value = 'b')

        self.assertRaises(timeout.Timeout,
                          timeout.with_timeout, DELAY, longer_timeout)

if __name__ == '__main__':
    unittest.main()
