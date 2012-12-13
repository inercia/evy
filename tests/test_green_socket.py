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
from evy.patched import time
from evy.green.threads import spawn, spawn_n, sleep

import errno
import os
import sys

from test_hub import check_hub



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


    def test_tcp_listener (self):
        socket = convenience.listen(('0.0.0.0', 0))
        assert socket.getsockname()[0] == '0.0.0.0'
        socket.close()
        check_hub()

    def test_connect_tcp (self):
        def accept_once (listenfd):
            try:
                conn, addr = listenfd.accept()
                fd = conn.makefile(mode = 'w')
                conn.close()
                fd.write('hello\n')
                fd.close()
            finally:
                listenfd.close()

        server = convenience.listen(('0.0.0.0', 0))
        spawn(accept_once, server)

        client = convenience.connect(('127.0.0.1', server.getsockname()[1]))
        fd = client.makefile()
        client.close()
        assert fd.readline() == 'hello\n'

        assert fd.read() == ''
        fd.close()

        check_hub()

    def test_getsockname (self):
        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        addr = listener.getsockname()
        self.assertNotEquals(addr[1], 0)

    @skipped
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




if __name__ == '__main__':
    main()
