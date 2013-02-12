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
Unit tests for socket timeout feature.
"""

import unittest
from test import test_support

# This requires the 'network' resource as given on the regrtest command line.
skip_expected = not test_support.is_resource_enabled('network')

import time

from evy.patched import socket


class TestGreenSocketTimeouts(unittest.TestCase):
    """
    Test case for socket.gettimeout() and socket.settimeout()
    """

    def setUp (self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tearDown (self):
        self.sock.close()

    def test_object_creation (self):
        # Test Socket creation
        self.assertEqual(self.sock.gettimeout(), None,
                         "timeout not disabled by default")

    def test_float_return_value (self):
        # Test return value of gettimeout()
        self.sock.settimeout(7.345)
        self.assertEqual(self.sock.gettimeout(), 7.345)

        self.sock.settimeout(3)
        self.assertEqual(self.sock.gettimeout(), 3)

        self.sock.settimeout(None)
        self.assertEqual(self.sock.gettimeout(), None)

    def test_return_type (self):
        # Test return type of gettimeout()
        self.sock.settimeout(1)
        self.assertEqual(type(self.sock.gettimeout()), type(1.0))

        self.sock.settimeout(3.9)
        self.assertEqual(type(self.sock.gettimeout()), type(1.0))

    def test_type_check (self):
        # Test type checking by settimeout()
        self.sock.settimeout(0)
        self.sock.settimeout(0L)
        self.sock.settimeout(0.0)
        self.sock.settimeout(None)
        self.assertRaises(TypeError, self.sock.settimeout, "")
        self.assertRaises(TypeError, self.sock.settimeout, u"")
        self.assertRaises(TypeError, self.sock.settimeout, ())
        self.assertRaises(TypeError, self.sock.settimeout, [])
        self.assertRaises(TypeError, self.sock.settimeout, {})
        self.assertRaises(TypeError, self.sock.settimeout, 0j)

    def test_range_check (self):
        # Test range checking by settimeout()
        self.assertRaises(ValueError, self.sock.settimeout, -1)
        self.assertRaises(ValueError, self.sock.settimeout, -1L)
        self.assertRaises(ValueError, self.sock.settimeout, -1.0)

    def test_timeout_then_blocking (self):
        # Test settimeout() followed by setblocking()
        self.sock.settimeout(10)
        self.sock.setblocking(1)
        self.assertEqual(self.sock.gettimeout(), None)
        self.sock.setblocking(0)
        self.assertEqual(self.sock.gettimeout(), 0.0)

        self.sock.settimeout(10)
        self.sock.setblocking(0)
        self.assertEqual(self.sock.gettimeout(), 0.0)
        self.sock.setblocking(1)
        self.assertEqual(self.sock.gettimeout(), None)

    def test_blocking_then_timeout (self):
        # Test setblocking() followed by settimeout()
        self.sock.setblocking(0)
        self.sock.settimeout(1)
        self.assertEqual(self.sock.gettimeout(), 1)

        self.sock.setblocking(1)
        self.sock.settimeout(1)
        self.assertEqual(self.sock.gettimeout(), 1)


class TimeoutTestCase(unittest.TestCase):
    """Test case for socket.socket() timeout functions"""

    # There are a number of tests here trying to make sure that an operation
    # doesn't take too much longer than expected.  But competing machine
    # activity makes it inevitable that such tests will fail at times.
    # When fuzz was at 1.0, I (tim) routinely saw bogus failures on Win2K
    # and Win98SE.  Boosting it to 2.0 helped a lot, but isn't a real
    # solution.
    fuzz = 2.0

    def setUp (self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr_remote = ('www.python.org.', 80)
        self.localhost = '127.0.0.1'

    def tearDown (self):
        self.sock.close()

    def test_connect_timeout (self):
        # Choose a private address that is unlikely to exist to prevent
        # failures due to the connect succeeding before the timeout.
        # Use a dotted IP address to avoid including the DNS lookup time
        # with the connect time.  This avoids failing the assertion that
        # the timeout occurred fast enough.
        addr = ('10.0.0.0', 12345)

        # Test connect() timeout
        _timeout = 0.001
        self.sock.settimeout(_timeout)

        _t1 = time.time()
        self.assertRaises(socket.error, self.sock.connect, addr)
        _t2 = time.time()

        _delta = abs(_t1 - _t2)
        self.assertTrue(_delta < _timeout + self.fuzz,
                        "timeout (%g) is more than %g seconds more than expected (%g)"
                        % (_delta, self.fuzz, _timeout))

    def test_recv_timeout (self):
        # Test recv() timeout
        _timeout = 0.02

        with test_support.transient_internet(self.addr_remote[0]):
            self.sock.connect(self.addr_remote)
            self.sock.settimeout(_timeout)

            _t1 = time.time()
            self.assertRaises(socket.timeout, self.sock.recv, 1024)
            _t2 = time.time()

            _delta = abs(_t1 - _t2)
            self.assertTrue(_delta < _timeout + self.fuzz,
                            "timeout (%g) is %g seconds more than expected (%g)"
                            % (_delta, self.fuzz, _timeout))

    def test_accept_timeout (self):
        # Test accept() timeout
        _timeout = 2
        self.sock.settimeout(_timeout)
        # Prevent "Address already in use" socket exceptions
        test_support.bind_port(self.sock, self.localhost)
        self.sock.listen(5)

        _t1 = time.time()
        self.assertRaises(socket.error, self.sock.accept)
        _t2 = time.time()

        _delta = abs(_t1 - _t2)
        self.assertTrue(_delta < _timeout + self.fuzz,
                        "timeout (%g) is %g seconds more than expected (%g)"
                        % (_delta, self.fuzz, _timeout))

    def test_recvfrom_timeout (self):
        # Test recvfrom() timeout
        _timeout = 2
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(_timeout)
        # Prevent "Address already in use" socket exceptions
        test_support.bind_port(self.sock, self.localhost)

        _t1 = time.time()
        self.assertRaises(socket.error, self.sock.recvfrom, 8192)
        _t2 = time.time()

        _delta = abs(_t1 - _t2)
        self.assertTrue(_delta < _timeout + self.fuzz,
                        "timeout (%g) is %g seconds more than expected (%g)"
                        % (_delta, self.fuzz, _timeout))



