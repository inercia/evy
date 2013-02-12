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


    def test_crucial_constants (self):
        # Testing for mission critical constants
        socket.AF_INET
        socket.SOCK_STREAM
        socket.SOCK_DGRAM
        socket.SOCK_RAW
        socket.SOCK_RDM
        socket.SOCK_SEQPACKET
        socket.SOL_SOCKET
        socket.SO_REUSEADDR


    def test_tcp_listener (self):
        socket = convenience.listen(('0.0.0.0', 0))
        assert socket.getsockname()[0] == '0.0.0.0'
        socket.close()
        check_hub()


    def test_getsockname (self):
        listener = sockets.GreenSocket()
        listener.bind(('', 0))
        addr = listener.getsockname()
        self.assertNotEquals(addr[1], 0)


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


    def test_ntoh (self):
        # This just checks that htons etc. are their own inverse,
        # when looking at the lower 16 or 32 bits.
        sizes = {socket.htonl: 32, socket.ntohl: 32,
                 socket.htons: 16, socket.ntohs: 16}
        for func, size in sizes.items():
            mask = (1L << size) - 1
            for i in (0, 1, 0xffff, ~0xffff, 2, 0x01234567, 0x76543210):
                self.assertEqual(i & mask, func(func(i & mask)) & mask)

            swapped = func(mask)
            self.assertEqual(swapped & mask, mask)
            self.assertRaises(OverflowError, func, 1L << 34)


    def test_ntoh_errors (self):
        good_values = [1, 2, 3, 1L, 2L, 3L]
        bad_values = [-1, -2, -3, -1L, -2L, -3L]
        for k in good_values:
            socket.ntohl(k)
            socket.ntohs(k)
            socket.htonl(k)
            socket.htons(k)
        for k in bad_values:
            self.assertRaises(OverflowError, socket.ntohl, k)
            self.assertRaises(OverflowError, socket.ntohs, k)
            self.assertRaises(OverflowError, socket.htonl, k)
            self.assertRaises(OverflowError, socket.htons, k)


    def test_getservbyname (self):
        eq = self.assertEqual
        # Find one service that exists, then check all the related interfaces.
        # I've ordered this by protocols that have both a tcp and udp
        # protocol, at least for modern Linuxes.
        if (sys.platform.startswith('linux') or
                sys.platform.startswith('freebsd') or
                sys.platform.startswith('netbsd') or
                    sys.platform == 'darwin'):
            # avoid the 'echo' service on this platform, as there is an
            # assumption breaking non-standard port/protocol entry
            services = ('daytime', 'qotd', 'domain')
        else:
            services = ('echo', 'daytime', 'domain')
        for service in services:
            try:
                port = socket.getservbyname(service, 'tcp')
                break
            except socket.error:
                pass
        else:
            raise socket.error
            # Try same call with optional protocol omitted
        port2 = socket.getservbyname(service)
        eq(port, port2)
        # Try udp, but don't barf it it doesn't exist
        try:
            udpport = socket.getservbyname(service, 'udp')
        except socket.error:
            udpport = None
        else:
            eq(udpport, port)
            # Now make sure the lookup by port returns the same service name
        eq(socket.getservbyport(port2), service)
        eq(socket.getservbyport(port, 'tcp'), service)
        if udpport is not None:
            eq(socket.getservbyport(udpport, 'udp'), service)
            # Make sure getservbyport does not accept out of range ports.
        self.assertRaises(OverflowError, socket.getservbyport, -1)
        self.assertRaises(OverflowError, socket.getservbyport, 65536)


    def test_default_timeout (self):
        # Testing default timeout
        # The default timeout should initially be None
        self.assertEqual(socket.getdefaulttimeout(), None)
        s = socket.socket()
        self.assertEqual(s.gettimeout(), None)
        s.close()

        # Set the default timeout to 10, and see if it propagates
        socket.setdefaulttimeout(10)
        self.assertEqual(socket.getdefaulttimeout(), 10)
        s = socket.socket()
        self.assertEqual(s.gettimeout(), 10)
        s.close()

        # Reset the default timeout to None, and see if it propagates
        socket.setdefaulttimeout(None)
        self.assertEqual(socket.getdefaulttimeout(), None)
        s = socket.socket()
        self.assertEqual(s.gettimeout(), None)
        s.close()

        # Check that setting it to an invalid value raises ValueError
        self.assertRaises(ValueError, socket.setdefaulttimeout, -1)

        # Check that setting it to an invalid type raises TypeError
        self.assertRaises(TypeError, socket.setdefaulttimeout, "spam")


    def test_sock_name (self):
        # Testing getsockname()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        sock.bind(("0.0.0.0", 0))
        name = sock.getsockname()
        # XXX(nnorwitz): http://tinyurl.com/os5jz seems to indicate
        # it reasonable to get the host's addr in addition to 0.0.0.0.
        # At least for eCos.  This is required for the S/390 to pass.
        try:
            my_ip_addr = socket.gethostbyname(socket.gethostname())
        except socket.error:
            # Probably name lookup wasn't set up right; skip this test
            return
        self.assertIn(name[0], ("0.0.0.0", my_ip_addr), '%s invalid' % name[0])

    def test_get_sock_opt (self):
        # Testing getsockopt()
        # We know a socket should start without reuse==0
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        reuse = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        self.assertFalse(reuse != 0, "initial mode is reuse")

    def test_set_sock_opt (self):
        # Testing setsockopt()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        reuse = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        self.assertFalse(reuse == 0, "failed to set reuse mode")


    def test_new_attributes (self):
        # testing .family, .type and .protocol
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.assertEqual(sock.family, socket.AF_INET)
        self.assertEqual(sock.type, socket.SOCK_STREAM)
        self.assertEqual(sock.proto, 0)
        sock.close()


    def test_getsockaddrarg (self):
        host = '0.0.0.0'
        port = 34555
        big_port = port + 65536
        neg_port = port - 65536
        sock = socket.socket()
        try:
            self.assertRaises(OverflowError, sock.bind, (host, big_port))
            self.assertRaises(OverflowError, sock.bind, (host, neg_port))
            sock.bind((host, port))
        finally:
            sock.close()


    def test_listen_backlog0 (self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(('0.0.0.0', 0))
        # backlog = 0
        srv.listen(0)
        srv.close()


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
