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


from weakref import proxy

from tests import LimitedTestCase, main, skipped, s2b

from evy.io import convenience
from evy.patched import socket

from evy.green.threads import spawn

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


class TestGreenSocketRefs(LimitedTestCase):
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

    def test_weakref (self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        p = proxy(s)
        self.assertEqual(p.fileno(), s.fileno())
        s.close()
        s = None
        try:
            p.fileno()
        except ReferenceError:
            pass
        else:
            self.fail('Socket proxy still exists')

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


    def test_makefile_closes (self):
        self.reset_timeout(100000)

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


if __name__ == '__main__':
    main()
