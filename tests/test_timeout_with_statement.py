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


"""
Tests with-statement behavior of Timeout class.  Don't import when
using Python 2.4.
"""

from __future__ import with_statement
import sys
import unittest
import weakref
import time

from tests import LimitedTestCase

from evy.greenthread import sleep
from evy.timeout import Timeout

DELAY = 0.01

class Error(Exception):
    pass


class Test(LimitedTestCase):

    def test_cancellation (self):
        """
        Testing that nothing happens if with-block finishes before the timeout expires
        """
        t = Timeout(DELAY * 2)
        sleep(0)  # make it pending
        assert t.pending, repr(t)
        with t:
            assert t.pending, repr(t)
            sleep(DELAY)
            # check if timer was actually cancelled
        assert not t.pending, repr(t)
        sleep(DELAY * 2)

    def test_raising_self (self):
        """
        Testing that an exception will be raised if it's not
        """
        try:
            with Timeout(DELAY) as t:
                sleep(DELAY * 2)
        except Timeout, ex:
            assert ex is t, (ex, t)
        else:
            raise AssertionError('must raise Timeout')

    def test_raising_self_true (self):
        """
        Testing that specifying True as the exception raises self as well
        """
        try:
            with Timeout(DELAY, True) as t:
                sleep(DELAY * 2)
        except Timeout, ex:
            assert ex is t, (ex, t)
        else:
            raise AssertionError('must raise Timeout')

    def test_raising_custom_exception (self):
        """
        Testing that ww can customize the exception raised
        """
        try:
            with Timeout(DELAY, IOError("Operation takes way too long")):
                sleep(DELAY * 2)
        except IOError, ex:
            assert str(ex) == "Operation takes way too long", repr(ex)

    def test_raising_exception_class (self):
        """
        Testing that we can provide classes instead of values should be possible too
        """
        try:
            with Timeout(DELAY, ValueError):
                sleep(DELAY * 2)
        except ValueError:
            pass

    def test_raising_exc_tuple (self):
        try:
            1 // 0
        except:
            try:
                with Timeout(DELAY, sys.exc_info()[0]):
                    sleep(DELAY * 2)
                    raise AssertionError('should not get there')
                raise AssertionError('should not get there')
            except ZeroDivisionError:
                pass
        else:
            raise AssertionError('should not get there')

    def test_cancel_timer_inside_block (self):
        """
        Testing that it's possible to cancel the timer inside the block
        """
        with Timeout(DELAY) as timer:
            timer.cancel()
            sleep(DELAY * 2)


    def test_silent_block (self):
        """
        Testing that, to silence the exception before exiting the block, we can pass
        False as second parameter.
        """
        XDELAY = 0.1
        start = time.time()
        with Timeout(XDELAY, False):
            sleep(XDELAY * 2)
        delta = (time.time() - start)
        assert delta < XDELAY * 2, delta


    def test_dummy_timer (self):
        """
        Testing that passing None as seconds disables the timer
        """
        with Timeout(None):
            sleep(DELAY)
        sleep(DELAY)

    def test_ref (self):
        err = Error()
        err_ref = weakref.ref(err)
        with Timeout(DELAY * 2, err):
            sleep(DELAY)
        del err
        assert not err_ref(), repr(err_ref())

    def test_nested_timeout (self):
        with Timeout(DELAY, False):
            with Timeout(DELAY * 2, False):
                sleep(DELAY * 3)
            raise AssertionError('should not get there')

        with Timeout(DELAY) as t1:
            with Timeout(DELAY * 2) as t2:
                try:
                    sleep(DELAY * 3)
                except Timeout, ex:
                    assert ex is t1, (ex, t1)
                assert not t1.pending, t1
                assert t2.pending, t2
            assert not t2.pending, t2

        with Timeout(DELAY * 2) as t1:
            with Timeout(DELAY) as t2:
                try:
                    sleep(DELAY * 3)
                except Timeout, ex:
                    assert ex is t2, (ex, t2)
                assert t1.pending, t1
                assert not t2.pending, t2
        assert not t1.pending, t1
