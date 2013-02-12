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
from test import test_support

import errno
import array

from evy.patched import socket, thread

from tests import SocketConnectedTest


MSG = 'Michael Gilfix was here\n'


class TestFileObjectClass(SocketConnectedTest):
    bufsize = -1 # Use default buffer size

    def __init__ (self, methodName = 'runTest'):
        SocketConnectedTest.__init__(self, methodName = methodName)

    def setUp (self):
        SocketConnectedTest.setUp(self)
        self.serv_file = self.cli_conn.makefile('rb', self.bufsize)

    def tearDown (self):
        self.serv_file.close()
        self.assertTrue(self.serv_file.closed)
        self.serv_file = None
        SocketConnectedTest.tearDown(self)

    def clientSetUp (self):
        SocketConnectedTest.clientSetUp(self)
        self.cli_file = self.serv_conn.makefile('wb')

    def clientTearDown (self):
        self.cli_file.close()
        self.assertTrue(self.cli_file.closed)
        self.cli_file = None
        SocketConnectedTest.clientTearDown(self)

    def test_small_read (self):
        """
        Performing small file read test
        """
        first_seg = self.serv_file.read(len(MSG) - 3)
        second_seg = self.serv_file.read(3)
        msg = first_seg + second_seg
        self.assertEqual(msg, MSG)

    def _test_small_read (self):
        self.cli_file.write(MSG)
        self.cli_file.flush()

    def test_full_read (self):
        # read until EOF
        msg = self.serv_file.read()
        self.assertEqual(msg, MSG)

    def _test_full_read (self):
        self.cli_file.write(MSG)
        self.cli_file.close()

    def test_unbuffered_read (self):
        """
        Performing unbuffered file read test
        """
        buf = ''
        while 1:
            char = self.serv_file.read(1)
            if not char:
                break
            buf += char
        self.assertEqual(buf, MSG)

    def _test_unbuffered_read (self):
        self.cli_file.write(MSG)
        self.cli_file.flush()

    def test_readline (self):
        # Performing file readline test
        line = self.serv_file.readline()
        self.assertEqual(line, MSG)

    def _test_readline (self):
        self.cli_file.write(MSG)
        self.cli_file.flush()

    def test_readline_after_read (self):
        a_baloo_is = self.serv_file.read(len("A baloo is"))
        self.assertEqual("A baloo is", a_baloo_is)
        _a_bear = self.serv_file.read(len(" a bear"))
        self.assertEqual(" a bear", _a_bear)
        line = self.serv_file.readline()
        self.assertEqual("\n", line)
        line = self.serv_file.readline()
        self.assertEqual("A BALOO IS A BEAR.\n", line)
        line = self.serv_file.readline()
        self.assertEqual(MSG, line)

    def _test_readline_after_read (self):
        self.cli_file.write("A baloo is a bear\n")
        self.cli_file.write("A BALOO IS A BEAR.\n")
        self.cli_file.write(MSG)
        self.cli_file.flush()

    def test_readline_after_read_no_newline (self):
        end_of_ = self.serv_file.read(len("End Of "))
        self.assertEqual("End Of ", end_of_)
        line = self.serv_file.readline()
        self.assertEqual("Line", line)

    def _test_readline_after_read_no_newline (self):
        self.cli_file.write("End Of Line")

    def test_closed_attr (self):
        self.assertTrue(not self.serv_file.closed)

    def _test_closed_attr (self):
        self.assertTrue(not self.cli_file.closed)


class TestFileObjectInterrupted(unittest.TestCase):
    """
    Test that the file object correctly handles EINTR internally.
    """

    class MockSocket(object):
        def __init__ (self, recv_funcs = ()):
            # A generator that returns callables that we'll call for each
            # call to recv().
            self._recv_step = iter(recv_funcs)

        def recv (self, size):
            return self._recv_step.next()()

    @staticmethod
    def _raise_eintr ():
        raise socket.error(errno.EINTR)

    def _test_readline (self, size = -1, **kwargs):
        mock_sock = self.MockSocket(recv_funcs = [
            lambda: "This is the first line\nAnd the sec",
            self._raise_eintr,
            lambda: "ond line is here\n",
            lambda: "",
        ])
        fo = socket._fileobject(mock_sock, **kwargs)
        self.assertEqual(fo.readline(size), "This is the first line\n")
        self.assertEqual(fo.readline(size), "And the second line is here\n")

    def _test_read (self, size = -1, **kwargs):
        mock_sock = self.MockSocket(recv_funcs = [
            lambda: "This is the first line\nAnd the sec",
            self._raise_eintr,
            lambda: "ond line is here\n",
            lambda: "",
        ])
        fo = socket._fileobject(mock_sock, **kwargs)
        self.assertEqual(fo.read(size), "This is the first line\n"
                                        "And the second line is here\n")

    def test_default (self):
        self._test_readline()
        self._test_readline(size = 100)
        self._test_read()
        self._test_read(size = 100)

    def test_with_1k_buffer (self):
        self._test_readline(bufsize = 1024)
        self._test_readline(size = 100, bufsize = 1024)
        self._test_read(bufsize = 1024)
        self._test_read(size = 100, bufsize = 1024)

    def _test_readline_no_buffer (self, size = -1):
        mock_sock = self.MockSocket(recv_funcs = [
            lambda: "aa",
            lambda: "\n",
            lambda: "BB",
            self._raise_eintr,
            lambda: "bb",
            lambda: "",
        ])
        fo = socket._fileobject(mock_sock, bufsize = 0)
        self.assertEqual(fo.readline(size), "aa\n")
        self.assertEqual(fo.readline(size), "BBbb")

    def test_no_buffer (self):
        self._test_readline_no_buffer()
        self._test_readline_no_buffer(size = 4)
        self._test_read(bufsize = 0)
        self._test_read(size = 100, bufsize = 0)


class TestUnbufferedTestFileObjectClass(TestFileObjectClass):
    """
    Repeat the tests from TestFileObjectClass with bufsize==0.

    In this case (and in this case only), it should be possible to
    create a file object, read a line from it, create another file
    object, read another line from it, without loss of data in the
    first file object's buffer.  Note that httplib relies on this
    when reading multiple requests from the same socket.
    """

    bufsize = 0 # Use unbuffered mode

    def test_unbuffered_readline (self):
        # Read a line, create a new file object, read another line with it
        line = self.serv_file.readline() # first line
        self.assertEqual(line, "A. " + MSG) # first line
        self.serv_file = self.cli_conn.makefile('rb', 0)
        line = self.serv_file.readline() # second line
        self.assertEqual(line, "B. " + MSG) # second line

    def _test_unbuffered_readline (self):
        self.cli_file.write("A. " + MSG)
        self.cli_file.write("B. " + MSG)
        self.cli_file.flush()


class TestLineBufferedFileObjectClass(TestFileObjectClass):
    bufsize = 1 # Default-buffered for reading; line-buffered for writing


class TestSmallBufferedFileObjectClass(TestFileObjectClass):
    bufsize = 2 # Exercise the buffering code


class TestUrllib2Fileobject(unittest.TestCase):
    # urllib2.HTTPHandler has "borrowed" socket._fileobject, and requires that
    # it close the socket if the close c'tor argument is true

    def testClose (self):
        class MockSocket:
            closed = False

            def flush (self): pass

            def close (self): self.closed = True

        # must not close unless we request it: the original use of _fileobject
        # by module socket requires that the underlying socket not be closed until
        # the _socketobject that created the _fileobject is closed
        s = MockSocket()
        f = socket._fileobject(s)
        f.close()
        self.assertTrue(not s.closed)

        s = MockSocket()
        f = socket._fileobject(s, close = True)
        f.close()
        self.assertTrue(s.closed)


class TestBufferIO(SocketConnectedTest):
    """
    Test the buffer versions of socket.recv() and socket.send().
    """

    def __init__ (self, methodName = 'runTest'):
        SocketConnectedTest.__init__(self, methodName = methodName)

    def test_recv_into_array (self):
        buf = array.array('c', ' ' * 1024)
        nbytes = self.cli_conn.recv_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf.tostring()[:len(MSG)]
        self.assertEqual(msg, MSG)

    def _test_recv_into_array (self):
        with test_support.check_py3k_warnings():
            buf = buffer(MSG)
        self.serv_conn.send(buf)

    def test_recv_into_bytearray (self):
        buf = bytearray(1024)
        nbytes = self.cli_conn.recv_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _test_recv_into_bytearray = _test_recv_into_array

    def test_recv_into_memoryview (self):
        buf = bytearray(1024)
        nbytes = self.cli_conn.recv_into(memoryview(buf))
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _test_recv_into_memoryview = _test_recv_into_array

    def test_recvfrom_into_array (self):
        buf = array.array('c', ' ' * 1024)
        nbytes, addr = self.cli_conn.recvfrom_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf.tostring()[:len(MSG)]
        self.assertEqual(msg, MSG)

    def _test_recvfrom_into_array (self):
        with test_support.check_py3k_warnings():
            buf = buffer(MSG)
        self.serv_conn.send(buf)

    def test_recvfrom_into_bytearray (self):
        buf = bytearray(1024)
        nbytes, addr = self.cli_conn.recvfrom_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _test_recvfrom_into_bytearray = _test_recvfrom_into_array

    def test_recvfrom_into_memoryview (self):
        buf = bytearray(1024)
        nbytes, addr = self.cli_conn.recvfrom_into(memoryview(buf))
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _test_recvfrom_into_memoryview = _test_recvfrom_into_array

