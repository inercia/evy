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
from tests import LimitedTestCase, main, skipped, s2b, skip_on_windows

from evy import event
from evy.io import sockets
from evy.io import convenience
from evy.patched import socket
from evy.patched import time
from evy.green.threads import spawn, sleep
from evy.timeout import Timeout
from evy.green.threads import TimeoutError

import os


def bufsized (sock, size = 1):
    """
    Resize both send and receive buffers on a socket.
    Useful for testing trampoline.  Returns the socket.

    >>> import socket
    >>> sock = bufsized(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, size)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)
    return sock


def min_buf_size ():
    """
    Return the minimum buffer size that the platform supports.
    """
    #test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1)
    #return test_sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
    return 65535




class TestGreenSocketSend(LimitedTestCase):

    TEST_TIMEOUT = 2


    def test_send_timeout (self):
        listener = bufsized(convenience.listen(('', 0)))

        evt = event.Event()

        def server ():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            sock = bufsized(sock)
            evt.wait()

        gt = spawn(server)

        addr = listener.getsockname()

        client = bufsized(sockets.GreenSocket())
        client.connect(addr)
        try:
            client.settimeout(0.00001)
            msg = s2b("A") * (100000)  # large enough number to overwhelm most buffers

            total_sent = 0
            # want to exceed the size of the OS buffer so it'll block in a
            # single send
            for x in range(10):
                total_sent += client.send(msg)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

    def test_sendall_timeout (self):
        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)

        evt = event.Event()

        def server ():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = spawn(server)

        addr = listener.getsockname()
        self.assertNotEqual(addr[1], 0)

        client = sockets.GreenSocket()
        client.settimeout(0.1)
        client.connect(addr)

        try:
            msg = s2b("A") * (8 * 1024 * 1024)

            # want to exceed the size of the OS buffer so it'll block
            client.sendall(msg)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()



    def test_full_duplex (self):
        large_data = s2b('*') * 10 * min_buf_size()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(50)
        bufsized(listener)

        def send_large (sock):
            sock.sendall(large_data)

        def read_large (sock):
            result = sock.recv(len(large_data))
            while len(result) < len(large_data):
                result += sock.recv(len(large_data))
                if result == '':
                    break
            self.assertEquals(result, large_data)

        def server ():
            (sock, addr) = listener.accept()
            sock = bufsized(sock)
            send_large_coro = spawn(send_large, sock)
            sleep(0)
            result = sock.recv(10)
            expected = s2b('hello world')
            while len(result) < len(expected) and result is not '':
                result += sock.recv(10)
            self.assertEquals(result, expected)
            send_large_coro.wait()

        server_evt = spawn(server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', listener.getsockname()[1]))
        bufsized(client)
        large_evt = spawn(read_large, client)
        sleep(0)
        client.sendall(s2b('hello world'))

        server_evt.wait()
        large_evt.wait()
        client.close()


    def test_sendall (self):
        # test adapted from Marcus Cavanaugh's email
        # it may legitimately take a while, but will eventually complete
        self.timer.cancel()
        second_bytes = 10

        def test_sendall_impl (many_bytes):
            bufsize = max(many_bytes // 15, 2)

            def sender (listener):
                (sock, addr) = listener.accept()
                sock = bufsized(sock, size = bufsize)
                sock.sendall(s2b('x') * many_bytes)
                sock.sendall(s2b('y') * second_bytes)

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("", 0))
            listener.listen(50)
            sender_coro = spawn(sender, listener)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            _, port = listener.getsockname()
            client.connect(('127.0.0.1', port))

            bufsized(client, size = bufsize)
            total = 0
            while total < many_bytes:
                data = client.recv(min(many_bytes - total, many_bytes // 10))
                if not data:
                    break
                total += len(data)

            total2 = 0
            while total < second_bytes:
                data = client.recv(second_bytes)
                if not data:
                    break
                total2 += len(data)

            sender_coro.wait()
            client.close()

        for how_many in (1000, 10000, 100000, 1000000):
            test_sendall_impl(how_many)


    def test_timeout_and_final_write (self):
        # This test verifies that a write on a socket that we've
        # stopped listening for doesn't result in an incorrect switch
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        server.listen(50)
        _, bound_port = server.getsockname()
        self.assertNotEqual(bound_port, 0)

        def sender (evt):
            s2, addr = server.accept()
            wrap_wfile = s2.makefile('w')

            sleep(0.02)
            wrap_wfile.write('hi')
            s2.close()
            evt.send('sent via event')

        from evy import event

        evt = event.Event()
        spawn(sender, evt)
        sleep(0)  # lets the socket enter accept mode, which
        # is necessary for connect to succeed on windows
        try:
            # try and get some data off of this pipe
            # but bail before any is sent
            Timeout(0.01)
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', bound_port))
            wrap_rfile = client.makefile()
            _c = wrap_rfile.read(1)
            self.fail()
        except socket.error, e:
            self.fail('could not connect to port %d: %s' % (bound_port, str(e)))
        except TimeoutError:
            pass

        result = evt.wait()
        self.assertEquals(result, 'sent via event')
        server.close()
        client.close()


    @skipped
    def test_invalid_connection (self):
        # find an unused port by creating a socket then closing it
        port = convenience.listen(('127.0.0.1', 0)).getsockname()[1]
        self.assertRaises(socket.error, convenience.connect, ('127.0.0.1', port))




if __name__ == '__main__':
    main()
