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
from evy import greenio
from evy import convenience
from evy.support import get_errno
from evy.green import socket
from evy.green import time
from evy.greenthread import spawn, spawn_n, sleep
from evy.timeout import Timeout
from evy.greenthread import TimeoutError

import errno

import os
import sys
import array
import tempfile, shutil

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




class TestGreenSocket(LimitedTestCase):

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
        gs = greenio.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(0.5)
        try:
            gs.connect(('192.0.2.2', 80))
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')
        except socket.error, e:
            # unreachable is also a valid outcome
            if not get_errno(e) in (errno.EHOSTUNREACH, errno.ENETUNREACH):
                raise

    def test_connect_invalid_ip (self):
        gs = greenio.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        gs.connect(('0.0.0.0', 80))


    def test_accept_timeout (self):
        gs = greenio.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
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
        gs = greenio.GreenSocket(socket.AF_INET, socket.SOCK_STREAM)
        gs.settimeout(0.1)
        #e = gs.connect_ex(('192.0.2.1', 80))
        e = gs.connect_ex(('255.255.0.1', 80))
        self.assertIn(e, (errno.EHOSTUNREACH, errno.ECONNREFUSED, errno.ENETUNREACH))
        #if not e in (errno.EHOSTUNREACH, errno.ECONNREFUSED, errno.ENETUNREACH):
        #    self.assertEquals(e, errno.EAGAIN)

    def test_getsockname (self):
        listener = greenio.GreenSocket()
        listener.bind(('', 0))
        addr = listener.getsockname()
        self.assertNotEquals(addr[1], 0)

    def test_bind_wrong_ip (self):
        listener = greenio.GreenSocket()
        try:
            listener.bind(('127.255.255.255', 0))
        except socket.error, e:
            self.assert_(hasattr(e, 'args'))
        except Exception, e:
            self.fail("unexpected exception '%s' %s" % (str(e), str(*e.args)))

        addr = listener.getsockname()
        self.assertNotEquals(addr[1], 0)

    def test_listen_without_bind (self):
        listener = greenio.GreenSocket()
        listener.listen(50)

    def test_recv (self):
        self.reset_timeout(1000000)

        listener = greenio.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)

        address, port = listener.getsockname()
        self.assertNotEquals(address, 0)

        accept_ready = event.Event()
        did_send_data = event.Event()
        did_receive_data = event.Event()

        def server ():
            # accept the connection in another greenlet
            accept_ready.send()
            sock, addr = listener.accept()
            s = 'hello'
            sock.send(s)
            did_send_data.send(s)

        gt_server = spawn(server)

        def client():
            client = greenio.GreenSocket()
            accept_ready.wait()
            client.connect(('127.0.0.1', port))
            received_data = client.recv(8192)
            did_receive_data.send(received_data)

        gt_client = spawn(client)

        sent_data = did_send_data.wait()
        received_data = did_receive_data.wait()

        self.assertEquals(sent_data, received_data)

    def test_recv_something (self):
        DATLEN = 5

        self.reset_timeout(1000000)

        listener = greenio.GreenSocket()
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
            client = greenio.GreenSocket()
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
        listener = greenio.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)

        accepting = event.Event()
        accepted = event.Event()

        def server ():
            # accept the connection in another greenlet
            accepting.send()
            sock, addr = listener.accept()
            accepted.wait()
        gt = spawn(server)

        address, port = listener.getsockname()
        self.assertNotEquals(address, 0)

        client = greenio.GreenSocket()
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
        gs = greenio.GreenSocket(socket.AF_INET, socket.SOCK_DGRAM)
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

        gs = greenio.GreenSocket(socket.AF_INET, socket.SOCK_DGRAM)
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

    def test_recv_into_timeout (self):
        buf = buffer(array.array('B'))

        listener = greenio.GreenSocket()
        listener.bind(('', 0))
        listener.listen(50)

        evt = event.Event()

        def server ():
            # accept the connection in another greenlet
            sock, addr = listener.accept()
            evt.wait()

        gt = spawn(server)

        addr = listener.getsockname()

        client = greenio.GreenSocket()
        client.settimeout(0.1)
        client.connect(addr)

        try:
            client.recv_into(buf)
            self.fail("socket.timeout not raised")
        except socket.timeout, e:
            self.assert_(hasattr(e, 'args'))
            self.assertEqual(e.args[0], 'timed out')

        evt.send()
        gt.wait()

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

        client = bufsized(greenio.GreenSocket())
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
        listener = greenio.GreenSocket()
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

        client = greenio.GreenSocket()
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

    def test_close_with_makefile (self):
        def accept_close_early (listener):
            # verify that the makefile and the socket are truly independent
            # by closing the socket prior to using the made file
            try:
                conn, addr = listener.accept()
                fd = conn.makefile('w')
                conn.close()
                fd.write('hello\n')
                fd.close()
                self.assertWriteToClosedFileRaises(fd)
                self.assertRaises(socket.error, conn.send, s2b('b'))
            finally:
                listener.close()

        def accept_close_late (listener):
            # verify that the makefile and the socket are truly independent
            # by closing the made file and then sending a character
            try:
                conn, addr = listener.accept()
                fd = conn.makefile('w')
                fd.write('hello')
                fd.close()
                conn.send(s2b('\n'))
                conn.close()
                self.assertWriteToClosedFileRaises(fd)
                self.assertRaises(socket.error, conn.send, s2b('b'))
            finally:
                listener.close()

        def did_it_work (server):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _, port = server.getsockname()
            print 'connecting to port', port
            client.connect(('127.0.0.1', port))
            fd = client.makefile()
            client.close()
            assert fd.readline() == 'hello\n'
            assert fd.read() == ''
            fd.close()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 61222))
        self.assertEqual(server.getsockname()[1], 61222)
        server.listen(50)
        killer = spawn(accept_close_early, server)
        did_it_work(server)
        killer.wait()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 0))
        server.listen(50)
        killer = spawn(accept_close_late, server)
        did_it_work(server)
        killer.wait()

    def test_del_closes_socket (self):
        def accept_once (listener):
            # delete/overwrite the original conn
            # object, only keeping the file object around
            # closing the file object should close everything
            try:
                conn, addr = listener.accept()
                conn = conn.makefile('w')
                conn.write('hello\n')
                conn.close()
                self.assertWriteToClosedFileRaises(conn)
            finally:
                listener.close()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        server.listen(50)
        killer = spawn(accept_once, server)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', server.getsockname()[1]))
        fd = client.makefile()
        client.close()
        assert fd.read() == 'hello\n'
        assert fd.read() == ''

        killer.wait()

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

        listener_ready = event.Event()

        def test_sendall_impl (many_bytes):
            bufsize = max(many_bytes // 15, 2)

            def sender (listener):
                listener_ready.send()
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

            listener_ready.wait()

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

    def test_wrap_socket (self):
        try:
            import ssl
        except ImportError:
            pass  # pre-2.6
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', 0))
            sock.listen(50)
            ssl_sock = ssl.wrap_socket(sock)

    def test_timeout_and_final_write (self):
        # This test verifies that a write on a socket that we've
        # stopped listening for doesn't result in an incorrect switch
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 0))
        server.listen(50)
        bound_port = server.getsockname()[1]
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
        except TimeoutError:
            pass

        result = evt.wait()
        self.assertEquals(result, 'sent via event')
        server.close()
        client.close()

    def test_raised_multiple_readers (self):

        def handle (sock, addr):
            sock.recv(1)
            sock.sendall("a")
            raise convenience.StopServe()

        listener = convenience.listen(('127.0.0.1', 0))
        server = spawn(convenience.serve, listener, handle)

        def reader (s):
            s.recv(1)

        s = convenience.connect(('127.0.0.1', listener.getsockname()[1]))
        a = spawn(reader, s)
        sleep(0)
        self.assertRaises(RuntimeError, s.recv, 1)
        s.sendall('b')
        a.wait()

    @skipped
    def test_closure (self):
        def spam_to_me (address):
            sock = convenience.connect(address)
            while True:
                try:
                    sock.sendall('hello world')
                except socket.error, e:
                    if get_errno(e) == errno.EPIPE:
                        return
                    raise

        server = convenience.listen(('127.0.0.1', 0))
        sender = spawn(spam_to_me, server.getsockname())
        client, address = server.accept()
        server.close()

        def reader ():
            try:
                while True:
                    data = client.recv(1024)
                    self.assert_(data)
            except socket.error, e:
                # we get an EBADF because client is closed in the same process
                # (but a different greenthread)
                if get_errno(e) != errno.EBADF:
                    raise

        def closer ():
            client.close()

        reader = spawn(reader)
        spawn_n(closer)
        reader.wait()
        sender.wait()

    @skipped
    def test_invalid_connection (self):
        # find an unused port by creating a socket then closing it
        port = convenience.listen(('127.0.0.1', 0)).getsockname()[1]
        self.assertRaises(socket.error, convenience.connect, ('127.0.0.1', port))


class TestGreenPipe(LimitedTestCase):
    @skip_on_windows
    def setUp (self):
        super(self.__class__, self).setUp()
        self.tempdir = tempfile.mkdtemp('_green_pipe_test')

    def tearDown (self):
        shutil.rmtree(self.tempdir)
        super(self.__class__, self).tearDown()

    def test_pipe (self):
        r, w = os.pipe()
        rf = greenio.GreenPipe(r, 'r');
        wf = greenio.GreenPipe(w, 'w', 0);

        def sender (f, content):
            for ch in content:
                sleep(0.0001)
                f.write(ch)
            f.close()

        one_line = "12345\n";
        spawn(sender, wf, one_line * 5)
        for i in xrange(5):
            line = rf.readline()
            sleep(0.01)
            self.assertEquals(line, one_line)
        self.assertEquals(rf.readline(), '')

    def test_pipe_read (self):
        # ensure that 'readline' works properly on GreenPipes when data is not
        # immediately available (fd is nonblocking, was raising EAGAIN)
        # also ensures that readline() terminates on '\n' and '\r\n'
        r, w = os.pipe()

        r = greenio.GreenPipe(r)
        w = greenio.GreenPipe(w, 'w')

        def writer ():
            sleep(.1)

            w.write('line\n')
            w.flush()

            w.write('line\r\n')
            w.flush()

        gt = spawn(writer)

        sleep(0)

        line = r.readline()
        self.assertEquals(line, 'line\n')

        line = r.readline()
        self.assertEquals(line, 'line\r\n')

        gt.wait()

    def test_pipe_writes_large_messages (self):
        r, w = os.pipe()

        r = greenio.GreenPipe(r)
        w = greenio.GreenPipe(w, 'w')

        large_message = "".join([1024 * chr(i) for i in xrange(65)])

        def writer ():
            w.write(large_message)
            w.close()

        gt = spawn(writer)

        for i in xrange(65):
            buf = r.read(1024)
            expected = 1024 * chr(i)
            self.assertEquals(buf, expected,
                              "expected=%r..%r, found=%r..%r iter=%d"
                              % (expected[:4], expected[-4:], buf[:4], buf[-4:], i))
        gt.wait()

    def test_seek_on_buffered_pipe (self):
        f = greenio.GreenPipe(self.tempdir + "/TestFile", 'w+', 1024)
        self.assertEquals(f.tell(), 0)
        f.seek(0, 2)
        self.assertEquals(f.tell(), 0)
        f.write('1234567890')
        f.seek(0, 2)
        self.assertEquals(f.tell(), 10)
        f.seek(0)
        value = f.read(1)
        self.assertEqual(value, '1')
        self.assertEquals(f.tell(), 1)
        value = f.read(1)
        self.assertEqual(value, '2')
        self.assertEquals(f.tell(), 2)
        f.seek(0, 1)
        self.assertEqual(f.readline(), '34567890')
        f.seek(0)
        self.assertEqual(f.readline(), '1234567890')
        f.seek(0, 2)
        self.assertEqual(f.readline(), '')

    def test_truncate (self):
        f = greenio.GreenPipe(self.tempdir + "/TestFile", 'w+', 1024)
        f.write('1234567890')
        f.truncate(9)
        self.assertEquals(f.tell(), 9)


class TestGreenIoStarvation(LimitedTestCase):
# fixme: this doesn't succeed, because of evy's predetermined
    # ordering.  two processes, one with server, one with client evys
    # might be more reliable?

    TEST_TIMEOUT = 300  # the test here might take a while depending on the OS

    @skipped  # by rdw, because it fails but it's not clear how to make it pass
    def test_server_starvation (self, sendloops = 15):
        recvsize = 2 * min_buf_size()
        sendsize = 10000 * recvsize

        results = [[] for i in xrange(5)]

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        listener.listen(50)

        base_time = time.time()

        def server (my_results):
            (sock, addr) = listener.accept()

            datasize = 0

            t1 = None
            t2 = None
            try:
                while True:
                    data = sock.recv(recvsize)
                    if not t1:
                        t1 = time.time() - base_time
                    if not data:
                        t2 = time.time() - base_time
                        my_results.append(datasize)
                        my_results.append((t1, t2))
                        break
                    datasize += len(data)
            finally:
                sock.close()

        def client ():
            pid = os.fork()
            if pid:
                return pid

            client = _orig_sock.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', port))

            bufsized(client, size = sendsize)

            for i in range(sendloops):
                client.sendall(s2b('*') * sendsize)
            client.close()
            os._exit(0)

        clients = []
        servers = []
        for r in results:
            servers.append(spawn(server, r))
        for r in results:
            clients.append(client())

        for s in servers:
            s.wait()
        for c in clients:
            os.waitpid(c, 0)

        listener.close()

        # now test that all of the server receive intervals overlap, and
        # that there were no errors.
        for r in results:
            assert len(r) == 2, "length is %d not 2!: %s\n%s" % (len(r), r, results)
            assert r[0] == sendsize * sendloops
            assert len(r[1]) == 2
            assert r[1][0] is not None
            assert r[1][1] is not None

        starttimes = sorted(r[1][0] for r in results)
        endtimes = sorted(r[1][1] for r in results)
        runlengths = sorted(r[1][1] - r[1][0] for r in results)

        # assert that the last task started before the first task ended
        # (our no-starvation condition)
        assert starttimes[-1] < endtimes[0], "Not overlapping: starts %s ends %s" % (
        starttimes, endtimes)

        maxstartdiff = starttimes[-1] - starttimes[0]

        assert maxstartdiff * 2 < runlengths[
                                  0], "Largest difference in starting times more than twice the shortest running time!"
        assert runlengths[0] * 2 > runlengths[
                                   -1], "Longest runtime more than twice as long as shortest!"


    def test_connection_refused (self):
        self.reset_timeout(1000000)

        # open and close a dummy server to find an unused port
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        _, port = server.getsockname()
        self.assertNotEqual(port, 0)
        server.close()
        del server

        s = socket.socket()
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
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        port = server.getsockname()[1]
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


if __name__ == '__main__':
    main()
