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


import socket
import os

from tests import LimitedTestCase, certificate_file, private_key_file
from tests import skip_if_no_ssl
from unittest import main

import evy
from evy import util
from evy.io.convenience import connect, listen
from evy.io.sockets import shutdown_safe
from evy.io.ssl import SSL
from evy.green import threads as greenthread





def listen_ssl_socket (address = ('127.0.0.1', 0)):
    sock = util.wrap_ssl(socket.socket(), certificate_file,
                         private_key_file, True)
    sock.bind(address)
    sock.listen(50)

    return sock


class SSLTest(LimitedTestCase):

    certificate_file = os.path.join(os.path.dirname(__file__), 'server.crt')
    private_key_file = os.path.join(os.path.dirname(__file__), 'server.key')

    @skip_if_no_ssl
    def test_duplex_response (self):
        def serve (listener):
            sock, addr = listener.accept()
            stuff = sock.read(8192)
            sock.write('response')

        sock = listen_ssl_socket()

        server_coro = evy.spawn(serve, sock)

        client = util.wrap_ssl(connect(('127.0.0.1', sock.getsockname()[1])))
        client.write('line 1\r\nline 2\r\n\r\n')
        self.assertEquals(client.read(8192), 'response')
        server_coro.wait()

    @skip_if_no_ssl
    def test_ssl_close (self):
        def serve (listener):
            sock, addr = listener.accept()
            stuff = sock.read(8192)
            try:
                self.assertEquals("", sock.read(8192))
            except SSL.ZeroReturnError:
                pass

        sock = listen_ssl_socket()

        server_coro = evy.spawn(serve, sock)

        raw_client = connect(('127.0.0.1', sock.getsockname()[1]))
        client = util.wrap_ssl(raw_client)
        client.write('X')
        shutdown_safe(client)
        client.close()
        server_coro.wait()

    @skip_if_no_ssl
    def test_ssl_connect (self):
        def serve (listener):
            sock, addr = listener.accept()
            stuff = sock.read(8192)

        sock = listen_ssl_socket()
        server_coro = evy.spawn(serve, sock)

        raw_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_client = util.wrap_ssl(raw_client)
        ssl_client.connect(('127.0.0.1', sock.getsockname()[1]))
        ssl_client.write('abc')
        shutdown_safe(ssl_client)
        ssl_client.close()
        server_coro.wait()

    @skip_if_no_ssl
    def test_ssl_connect2 (self):
        def accept_once (listenfd):
            try:
                conn, addr = listenfd.accept()
                conn.write('hello\r\n')
                shutdown_safe(conn)
                conn.close()
            finally:
                shutdown_safe(listenfd)
                listenfd.close()

        server = ssl_listener(('0.0.0.0', 0),
                              self.certificate_file,
                              self.private_key_file)
        greenthread.spawn(accept_once, server)

        raw_client = connect(('127.0.0.1', server.getsockname()[1]))
        client = util.wrap_ssl(raw_client)
        fd = socket._fileobject(client, 'rb', 8192)

        assert fd.readline() == 'hello\r\n'
        try:
            self.assertEquals('', fd.read(10))
        except SSL.ZeroReturnError:
            # if it's a GreenSSL object it'll do this
            pass
        shutdown_safe(client)
        client.close()

    @skip_if_no_ssl
    def test_ssl_unwrap (self):
        def serve ():
            sock, addr = listener.accept()
            self.assertEquals(sock.recv(6), 'before')
            sock_ssl = util.wrap_ssl(sock, certificate_file, private_key_file,
                                     server_side = True)
            sock_ssl.do_handshake()
            self.assertEquals(sock_ssl.read(6), 'during')
            sock2 = sock_ssl.unwrap()
            self.assertEquals(sock2.recv(5), 'after')
            sock2.close()

        listener = listen(('127.0.0.1', 0))
        server_coro = evy.spawn(serve)
        client = connect((listener.getsockname()))
        client.send('before')
        client_ssl = util.wrap_ssl(client)
        client_ssl.do_handshake()
        client_ssl.write('during')
        client2 = client_ssl.unwrap()
        client2.send('after')
        server_coro.wait()


class SocketSSLTest(LimitedTestCase):


    @skip_if_no_ssl
    def test_greensslobject (self):
        import warnings
        # disabling socket.ssl warnings because we're testing it here
        warnings.filterwarnings(action = 'ignore',
                                message = '.*socket.ssl.*',
                                category = DeprecationWarning)

        def serve (listener):
            sock, addr = listener.accept()
            sock.write('content')
            shutdown_safe(sock)
            sock.close()

        listener = listen_ssl_socket(('', 0))
        killer = evy.spawn(serve, listener)
        from evy.patched.socket import ssl

        client = ssl(connect(('localhost', listener.getsockname()[1])))
        self.assertEquals(client.read(1024), 'content')
        self.assertEquals(client.read(1024), '')


if __name__ == '__main__':
    main()
