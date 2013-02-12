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
import errno

import evy
from evy import event

from evy.patched import urllib2
from evy.patched import httplib
from evy.io.sockets import shutdown_safe
from evy.io.convenience import connect, listen
from evy.green.threads import sleep
from evy.web.websocket import WebSocket, WebSocketWSGI

from tests import mock, LimitedTestCase, certificate_file, private_key_file
from tests import skip_if_no_ssl
from tests.test_wsgi import _TestBase


# demo app
def handle (ws):
    if ws.path == '/echo':
        while True:
            m = ws.wait()
            if m is None:
                break
            ws.send(m)
    elif ws.path == '/range':
        for i in xrange(10):
            ws.send("msg %d" % i)
            sleep(0.01)
    elif ws.path == '/error':
        # some random socket error that we shouldn't normally get
        raise socket.error(errno.ENOTSOCK)
    else:
        ws.close()


wsapp = WebSocketWSGI(handle)


class TestWebSocket(_TestBase):
    TEST_TIMEOUT = 5

    def set_site (self):
        self.site = wsapp

    def test_incorrect_headers (self):
        def raiser ():
            try:
                urllib2.urlopen("http://localhost:%s/echo" % self.port)
            except urllib2.HTTPError, e:
                self.assertEqual(e.code, 400)
                raise

        self.assertRaises(urllib2.HTTPError, raiser)

    def test_incomplete_headers_75 (self):
        headers = dict(kv.split(': ') for kv in [
            "Upgrade: WebSocket",
            # NOTE: intentionally no connection header
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "WebSocket-Protocol: ws",
        ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers = headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')

    def test_incomplete_headers_76 (self):
        # First test: Missing Connection:
        headers = dict(kv.split(': ') for kv in [
            "Upgrade: WebSocket",
            # NOTE: intentionally no connection header
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
        ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers = headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')

        # Now, miss off key2
        headers = dict(kv.split(': ') for kv in [
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            # NOTE: Intentionally no Key2 header
        ])
        http = httplib.HTTPConnection('localhost', self.port)
        http.request("GET", "/echo", headers = headers)
        resp = http.getresponse()

        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.getheader('connection'), 'close')
        self.assertEqual(resp.read(), '')

    def test_correct_upgrade_request_75 (self):
        connect_data = [
            "GET /echo HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "WebSocket-Protocol: ws",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n')
        result = sock.recv(1024)
        ## The server responds the correct Websocket handshake
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 Web Socket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'WebSocket-Origin: http://localhost:%s' % self.port,
                                      'WebSocket-Location: ws://localhost:%s/echo\r\n\r\n' % self.port]))

    def test_correct_upgrade_request_76 (self):
        connect_data = [
            "GET /echo HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        result = sock.recv(1024)
        ## The server responds the correct Websocket handshake
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 WebSocket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'Sec-WebSocket-Origin: http://localhost:%s' % self.port,
                                      'Sec-WebSocket-Protocol: ws',
                                      'Sec-WebSocket-Location: ws://localhost:%s/echo\r\n\r\n8jKS\'y:G*Co,Wxa-' % self.port]))


    def test_query_string (self):
        # verify that the query string comes out the other side unscathed
        connect_data = [
            "GET /echo?query_string HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        result = sock.recv(1024)
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 WebSocket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'Sec-WebSocket-Origin: http://localhost:%s' % self.port,
                                      'Sec-WebSocket-Protocol: ws',
                                      'Sec-WebSocket-Location: ws://localhost:%s/echo?query_string\r\n\r\n8jKS\'y:G*Co,Wxa-' % self.port]))

    def test_empty_query_string (self):
        # verify that a single trailing ? doesn't get nuked
        connect_data = [
            "GET /echo? HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        result = sock.recv(1024)
        self.assertEqual(result,
                         '\r\n'.join(['HTTP/1.1 101 WebSocket Protocol Handshake',
                                      'Upgrade: WebSocket',
                                      'Connection: Upgrade',
                                      'Sec-WebSocket-Origin: http://localhost:%s' % self.port,
                                      'Sec-WebSocket-Protocol: ws',
                                      'Sec-WebSocket-Location: ws://localhost:%s/echo?\r\n\r\n8jKS\'y:G*Co,Wxa-' % self.port]))


    def test_sending_messages_to_websocket_75 (self):
        connect_data = [
            "GET /echo HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "WebSocket-Protocol: ws",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n')
        first_resp = sock.recv(1024)
        sock.sendall('\x00hello\xFF')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00hello\xff')
        sock.sendall('\x00start')
        sleep(0.001)
        sock.sendall(' end\xff')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00start end\xff')
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        sleep(0.01)

    def test_sending_messages_to_websocket_76 (self):
        connect_data = [
            "GET /echo HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        first_resp = sock.recv(1024)
        sock.sendall('\x00hello\xFF')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00hello\xff')
        sock.sendall('\x00start')
        sleep(0.001)
        sock.sendall(' end\xff')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00start end\xff')
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        sleep(0.01)

    def test_getting_messages_from_websocket_75 (self):
        connect_data = [
            "GET /range HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "WebSocket-Protocol: ws",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n')
        resp = sock.recv(1024)
        headers, result = resp.split('\r\n\r\n')
        msgs = [result.strip('\x00\xff')]
        cnt = 10
        while cnt:
            msgs.append(sock.recv(20).strip('\x00\xff'))
            cnt -= 1
            # Last item in msgs is an empty string
        self.assertEqual(msgs[:-1], ['msg %d' % i for i in range(10)])

    def test_getting_messages_from_websocket_76 (self):
        connect_data = [
            "GET /range HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)
        headers, result = resp.split('\r\n\r\n')
        msgs = [result[16:].strip('\x00\xff')]
        cnt = 10
        while cnt:
            msgs.append(sock.recv(20).strip('\x00\xff'))
            cnt -= 1
            # Last item in msgs is an empty string
        self.assertEqual(msgs[:-1], ['msg %d' % i for i in range(10)])

    def test_breaking_the_connection_75 (self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site

        def error_detector (environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)

        self.site = error_detector
        self.spawn_server()
        connect_data = [
            "GET /range HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "WebSocket-Protocol: ws",
        ]
        sock = connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n')
        resp = sock.recv(1024)  # get the headers
        sock.close()  # close while the app is running
        done_with_request.wait()
        self.assert_(not error_detected[0])

    def test_breaking_the_connection_76 (self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site

        def error_detector (environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)

        self.site = error_detector
        self.spawn_server()
        connect_data = [
            "GET /range HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)  # get the headers
        sock.close()  # close while the app is running
        done_with_request.wait()
        self.assert_(not error_detected[0])

    def test_client_closing_connection_76 (self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site

        def error_detector (environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)

        self.site = error_detector
        self.spawn_server()
        connect_data = [
            "GET /echo HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)  # get the headers
        sock.sendall('\xff\x00') # "Close the connection" packet.
        done_with_request.wait()
        self.assert_(not error_detected[0])

    def test_client_invalid_packet_76 (self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site

        def error_detector (environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)

        self.site = error_detector
        self.spawn_server()
        connect_data = [
            "GET /echo HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)  # get the headers
        sock.sendall('\xef\x00') # Weird packet.
        done_with_request.wait()
        self.assert_(error_detected[0])

    def test_server_closing_connect_76 (self):
        connect_data = [
            "GET / HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)
        headers, result = resp.split('\r\n\r\n')
        # The remote server should have immediately closed the connection.
        self.assertEqual(result[16:], '\xff\x00')

    def test_app_socket_errors_75 (self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site

        def error_detector (environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)

        self.site = error_detector
        self.spawn_server()
        connect_data = [
            "GET /error HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "WebSocket-Protocol: ws",
        ]
        sock = connect(('localhost', self.port))
        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n')
        resp = sock.recv(1024)
        done_with_request.wait()
        self.assert_(error_detected[0])

    def test_app_socket_errors_76 (self):
        error_detected = [False]
        done_with_request = event.Event()
        site = self.site

        def error_detector (environ, start_response):
            try:
                try:
                    return site(environ, start_response)
                except:
                    error_detected[0] = True
                    raise
            finally:
                done_with_request.send(True)

        self.site = error_detector
        self.spawn_server()
        connect_data = [
            "GET /error HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = connect(
            ('localhost', self.port))
        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        resp = sock.recv(1024)
        done_with_request.wait()
        self.assert_(error_detected[0])


class TestWebSocketSSL(_TestBase):
    def set_site (self):
        self.site = wsapp

    @skip_if_no_ssl
    def test_ssl_sending_messages (self):
        s = evy.wrap_ssl(listen(('localhost', 0)),
                         certfile = certificate_file,
                         keyfile = private_key_file,
                         server_side = True)
        self.spawn_server(sock = s)
        connect_data = [
            "GET /echo HTTP/1.1",
            "Upgrade: WebSocket",
            "Connection: Upgrade",
            "Host: localhost:%s" % self.port,
            "Origin: http://localhost:%s" % self.port,
            "Sec-WebSocket-Protocol: ws",
            "Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5",
            "Sec-WebSocket-Key2: 12998 5 Y3 1  .P00",
        ]
        sock = evy.wrap_ssl(connect(
            ('localhost', self.port)))

        sock.sendall('\r\n'.join(connect_data) + '\r\n\r\n^n:ds[4U')
        first_resp = sock.recv(1024)
        # make sure it sets the wss: protocol on the location header
        loc_line = [x for x in first_resp.split("\r\n")
                    if x.lower().startswith('sec-websocket-location')][0]
        self.assert_("wss://localhost" in loc_line,
                     "Expecting wss protocol in location: %s" % loc_line)
        sock.sendall('\x00hello\xFF')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00hello\xff')
        sock.sendall('\x00start')
        sleep(0.001)
        sock.sendall(' end\xff')
        result = sock.recv(1024)
        self.assertEqual(result, '\x00start end\xff')
        shutdown_safe(sock)
        sock.close()
        sleep(0.01)


class TestWebSocketObject(LimitedTestCase):
    def setUp (self):
        self.mock_socket = s = mock.Mock()
        self.environ = env = dict(HTTP_ORIGIN = 'http://localhost', HTTP_WEBSOCKET_PROTOCOL = 'ws',
                                  PATH_INFO = 'test')

        self.test_ws = WebSocket(s, env)
        super(TestWebSocketObject, self).setUp()

    def test_recieve (self):
        ws = self.test_ws
        ws.socket.recv.return_value = '\x00hello\xFF'
        self.assertEqual(ws.wait(), 'hello')
        self.assertEqual(ws._buf, '')
        self.assertEqual(len(ws._msgs), 0)
        ws.socket.recv.return_value = ''
        self.assertEqual(ws.wait(), None)
        self.assertEqual(ws._buf, '')
        self.assertEqual(len(ws._msgs), 0)


    def test_send_to_ws (self):
        ws = self.test_ws
        ws.send(u'hello')
        self.assert_(ws.socket.sendall.called_with("\x00hello\xFF"))
        ws.send(10)
        self.assert_(ws.socket.sendall.called_with("\x0010\xFF"))

    def test_close_ws (self):
        ws = self.test_ws
        ws.close()
        self.assert_(ws.socket.shutdown.called_with(True))
