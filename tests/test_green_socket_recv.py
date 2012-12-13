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
from evy.support import get_errno
from evy.patched import socket
from evy.patched import time
from evy.green.threads import spawn, spawn_n, sleep
from evy.timeout import Timeout
from evy.green.threads import TimeoutError, waitall

import errno

import os
import sys
import array
import tempfile, shutil



class TestGreenSocketRecv(LimitedTestCase):

    TEST_TIMEOUT = 1

    def test_recv (self):
        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)

        address, port = listener.getsockname()
        self.assertNotEquals(address, 0)

        accepting = event.Event()
        received = event.Event()
        sent_data = '1234567890'


        def server ():
            # accept the connection in another greenlet
            accepting.send()
            sock, addr = listener.accept()
            sock.send(sent_data)
        gt_server = spawn(server)

        def client():
            client = sockets.GreenSocket()
            accepting.wait()
            sleep(0.5)
            client.connect(('127.0.0.1', port))
            received_data = client.recv(5000)
            received.send(received_data)
        gt_client = spawn(client)

        waitall(gt_client, gt_server)

        received_data = received.wait()

        self.assertEquals(sent_data, received_data)

    def test_recv_something (self):
        DATLEN = 5

        self.reset_timeout(1000000)

        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)

        address, port = listener.getsockname()
        self.assertNotEquals(address, 0)

        accepting = event.Event()
        sent = event.Event()
        received = event.Event()

        def server ():
            # accept the connection in another greenlet
            accepting.send()
            sock, addr = listener.accept()
            s = '1234567890'
            sock.send(s)
            sent.send(s)

        gt_server = spawn(server)

        def client():
            client = sockets.GreenSocket()
            accepting.wait()
            sleep(0.5)
            client.connect(('127.0.0.1', port))
            received_data = client.recv(DATLEN)
            received.send(received_data)

        gt_client = spawn(client)

        sent_data = sent.wait()
        received_data = received.wait()

        self.assertEquals(sent_data[:DATLEN], received_data)



    def test_recv_timeout (self):
        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)
        address, port = listener.getsockname()
        self.assertNotEquals(address, 0)

        accepting = event.Event()
        accepted = event.Event()

        def server ():
            # accept the connection in another greenlet
            accepting.send()
            sock, addr = listener.accept()
            accepted.wait()
        gt = spawn(server)

        client = sockets.GreenSocket()
        client.settimeout(0.1)

        accepting.wait()
        client.connect(('127.0.0.1', port))

        try:
            client.recv(8192)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        accepted.send()
        gt.wait()

    def test_recvfrom_timeout (self):
        gs = sockets.GreenSocket(socket.AF_INET, socket.SOCK_DGRAM)
        gs.settimeout(.1)
        gs.bind(('', 0))

        try:
            gs.recvfrom(8192)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')
        except:
            self.fail('unknown exception')

    def test_recvfrom_into_timeout (self):
        buf = buffer(array.array('B'))

        gs = sockets.GreenSocket(socket.AF_INET, socket.SOCK_DGRAM)
        gs.settimeout(.1)
        gs.bind(('', 0))

        try:
            gs.recvfrom_into(buf)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')
        except:
            self.fail('unknown exception')

    def test_recv_into (self):
        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)

        address, port = listener.getsockname()
        self.assertNotEquals(address, 0)

        accepting = event.Event()
        received = event.Event()
        sent_data = '1234567890'

        def server ():
            # accept the connection in another greenlet
            accepting.send()
            sock, addr = listener.accept()
            sock.send(sent_data)
        gt_server = spawn(server)

        def client():
            buf = ''
            client = sockets.GreenSocket()
            accepting.wait()
            sleep(0.5)
            client.connect(('127.0.0.1', port))
            client.recv_into(buf, 5000)
            received.send(buf)
        gt_client = spawn(client)

        waitall(gt_client, gt_server)

        received_data = received.wait()

        self.assertEquals(sent_data, received_data)


    def test_recv_into_timeout (self):
        buf = buffer(array.array('B'))

        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)
        address, port = listener.getsockname()
        self.assertNotEquals(address, 0)

        accepting = event.Event()
        accepted = event.Event()

        def server ():
            # accept the connection in another greenlet
            accepting.send()
            sock, addr = listener.accept()
            accepted.wait()
        gt = spawn(server)

        client = sockets.GreenSocket()
        client.settimeout(0.1)

        accepting.wait()
        client.connect(('127.0.0.1', port))

        try:
            client.recv_into(buf, 100)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        accepted.send()
        gt.wait()



if __name__ == '__main__':
    main()
