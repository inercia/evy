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


import socket as _orig_sock
from tests import LimitedTestCase, main, skipped, s2b

from evy.io import sockets
from evy.io import convenience
from evy.support import get_errno
from evy.patched import socket
from evy.green.threads import spawn, sleep

import errno
import sys




class TestGreenSocketErrors(LimitedTestCase):

    TEST_TIMEOUT = 2

    def assertWriteToClosedFileRaises (self, fd):
        if sys.version_info[0] < 3:
            # 2.x socket._fileobjects are odd: writes don't check
            # whether the socket is closed or not, and you get an
            # AttributeError during flush if it is closed
            fd.write('a')
            self.assertRaises(Exception, fd.flush)
        else:
            # 3.x poll write to closed file-like pbject raises ValueError
            self.assertRaises(ValueError, fd.write, 'a')

    def test_connect_timeout (self):
        gs = sockets.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(0.5)
        try:
            gs.connect(('192.0.2.2', 80))
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')
        except socket.error, e:
            # unreachable is also a valid outcome
            if not get_errno(e) in (errno.EHOSTUNREACH, errno.ENETUNREACH):
                raise
        except Exception, e:
            self.fail("unexpected exception '%s' %s" % (str(e), str(*e.args)))

        self.fail("socket.timeout not raised")

    def test_connect_invalid_ip (self):
        gs = sockets.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        gs.connect(('0.0.0.0', 80))


    def test_accept_timeout (self):
        gs = sockets.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(0.1)
        gs.bind(('', 0))
        gs.listen(50)
        self.assertNotEqual(gs.getsockname()[1], 0)

        try:
            gs.accept()
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')
        except Exception, e:
            self.fail("unexpected exception '%s' %s" % (str(e), str(*e.args)))


    def test_connect_ex_timeout (self):
        gs = sockets.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(0.1)
        #e = gs.connect_ex(('192.0.2.1', 80))
        e = gs.connect_ex(('255.255.0.1', 80))
        self.assertIn(e, (errno.EHOSTUNREACH, errno.ECONNREFUSED, errno.ENETUNREACH, errno.ETIME, errno.EAGAIN))

    def test_connection_refused (self):
        # open and close a dummy server to find an unused port
        server = sockets.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        _, port = server.getsockname()
        self.assertNotEqual(port, 0)
        server.close()
        del server

        s = sockets.GreenSocket()
        try:
            s.connect(('127.0.0.1', port))
            self.fail("Shouldn't have connected")
        except socket.error, ex:
            code, text = ex.args
            assert code in [111, 61, 10061], (code, text)
            assert 'refused' in text.lower(), (code, text)
        except Exception, e:
            self.fail('unexpected exception: %s' % str(e))

    def test_timeout_real_socket (self):
        """
        Test underlying socket behavior to ensure correspondence
        between green sockets and the underlying socket module.
        """
        return self.test_timeout(socket = _orig_sock)

    def test_timeout (self, socket = socket):
        """
        Test that the socket timeout exception works correctly.
        """
        server = sockets.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        _, port = server.getsockname()
        self.assertNotEqual(port, 0)

        s = socket.socket()

        s.connect(('127.0.0.1', port))

        cs, addr = server.accept()
        cs.settimeout(1)
        try:
            try:
                cs.recv(1024)
                self.fail("Should have timed out")
            except socket.timeout, ex:
                assert hasattr(ex, 'args')
                assert len(ex.args) == 1
                assert ex.args[0] == 'timed out'
        finally:
            s.close()
            cs.close()
            server.close()

    def test_getsockname (self):
        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        addr = listener.getsockname()
        self.assertNotEquals(addr[1], 0)

    def test_bind_wrong_ip (self):
        listener = sockets.GreenSocket()
        try:
            listener.bind(('127.255.255.255', 0))
        except socket.error, e:
            self.assert_(hasattr(e, 'args'))
        except Exception, e:
            self.fail("unexpected exception '%s' %s" % (str(e), str(*e.args)))

        addr = listener.getsockname()
        self.assertNotEquals(addr[1], 0)


    def test_listen_without_bind (self):
        listener = sockets.GreenSocket()
        listener.listen(50)

    def test_raised_multiple_readers (self):

        def handle (sock, addr):
            sock.recv(1)
            sock.sendall("a")
            raise convenience.StopServe()

        listener = convenience.listen(('127.0.0.1', 0))
        server = spawn(convenience.serve, listener, handle)
        _, port = listener.getsockname()

        def reader (s):
            s.recv(1)

        sleep(0)
        s = convenience.connect(('127.0.0.1', port))
        a = spawn(reader, s)
        sleep(0)
        self.assertRaises(RuntimeError, s.recv, 1)
        s.sendall('b')
        a.wait()

    @skipped
    def test_invalid_connection (self):
        # find an unused port by creating a socket then closing it
        port = convenience.listen(('127.0.0.1', 0)).getsockname()[1]
        self.assertRaises(socket.error, convenience.connect, ('127.0.0.1', port))





if __name__ == '__main__':
    main()
