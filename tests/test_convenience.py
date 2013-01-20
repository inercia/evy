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


import os

from evy import event
from evy.io import convenience
from evy.patched import socket
from evy.green.threads import spawn, sleep
from evy.timeout import with_timeout

from tests import LimitedTestCase, s2b, skip_if_no_ssl

certificate_file = os.path.join(os.path.dirname(__file__), 'server.crt')
private_key_file = os.path.join(os.path.dirname(__file__), 'server.key')



class TestConvenience(LimitedTestCase):

    def setUp (self):
        super(TestConvenience, self).setUp()
        from evy.tools import debug

        debug.hub_exceptions(False)

    def tearDown (self):
        super(TestConvenience, self).tearDown()
        from evy.tools import debug

        debug.hub_exceptions(True)

    def test_exiting_server (self):
        # tests that the server closes the client sock on handle() exit
        def closer (sock, addr):
            pass

        l = convenience.listen(('localhost', 0))
        gt = spawn(convenience.serve, l, closer)
        client = convenience.connect(('localhost', l.getsockname()[1]))
        client.sendall(s2b('a'))
        self.assertFalse(client.recv(100))
        gt.kill()


    def test_excepting_server (self):
        # tests that the server closes the client sock on handle() exception
        def crasher (sock, addr):
            sock.recv(1024)
            0 // 0

        l = convenience.listen(('localhost', 0))
        gt = spawn(convenience.serve, l, crasher)
        _, port = l.getsockname()
        client = convenience.connect(('localhost', port))
        client.sendall(s2b('a'))
        self.assertRaises(ZeroDivisionError, gt.wait)
        self.assertFalse(client.recv(100))

    def test_excepting_server_already_closed (self):
        # same as above but with explicit clsoe before crash
        def crasher (sock, addr):
            sock.recv(1024)
            sock.close()
            0 // 0

        l = convenience.listen(('localhost', 0))
        gt = spawn(convenience.serve, l, crasher)
        client = convenience.connect(('localhost', l.getsockname()[1]))
        client.sendall(s2b('a'))
        self.assertRaises(ZeroDivisionError, gt.wait)
        self.assertFalse(client.recv(100))

    def test_called_for_each_connection (self):
        hits = [0]

        def counter (sock, addr):
            hits[0] += 1

        l = convenience.listen(('localhost', 0))
        gt = spawn(convenience.serve, l, counter)
        _, port = l.getsockname()

        for i in xrange(100):
            client = convenience.connect(('localhost', port))
            self.assertFalse(client.recv(100))

        gt.kill()
        self.assertEqual(100, hits[0])

    def test_blocking (self):
        l = convenience.listen(('localhost', 0))
        x = with_timeout(0.01,
                                  convenience.serve, l, lambda c, a: None,
                                  timeout_value = "timeout")
        self.assertEqual(x, "timeout")

    def test_raising_stopserve (self):
        def stopit (conn, addr):
            raise convenience.StopServe()

        l = convenience.listen(('localhost', 0))
        # connect to trigger a call to stopit
        gt = spawn(convenience.connect,
            ('localhost', l.getsockname()[1]))
        convenience.serve(l, stopit)
        gt.wait()

    def test_concurrency (self):
        evt = event.Event()

        def waiter (sock, addr):
            sock.sendall(s2b('hi'))
            evt.wait()

        l = convenience.listen(('localhost', 0))
        gt = spawn(convenience.serve, l, waiter, 5)

        def test_client ():
            c = convenience.connect(('localhost', l.getsockname()[1]))
            # verify the client is connected by getting data
            self.assertEquals(s2b('hi'), c.recv(2))
            return c

        clients = [test_client() for i in xrange(5)]
        # very next client should not get anything
        x = with_timeout(0.01, test_client, timeout_value = "timed out")
        self.assertEquals(x, "timed out")

    @skip_if_no_ssl
    def test_wrap_ssl (self):
        server = convenience.wrap_ssl(convenience.listen(('localhost', 0)),
                                   certfile = certificate_file,
                                   keyfile = private_key_file, server_side = True)
        port = server.getsockname()[1]

        def handle (sock, addr):
            sock.sendall(sock.recv(1024))
            raise convenience.StopServe()

        spawn(convenience.serve, server, handle)
        client = convenience.wrap_ssl(convenience.connect(('localhost', port)))
        client.sendall("echo")
        self.assertEquals("echo", client.recv(1024))

    def test_socket_reuse (self):
        lsock1 = convenience.listen(('localhost', 0))
        port = lsock1.getsockname()[1]

        def same_socket ():
            return convenience.listen(('localhost', port))

        self.assertRaises(socket.error, same_socket)
        lsock1.close()
        assert same_socket()

