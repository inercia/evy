import os

import evy
from evy import event
from evy.green import socket
from tests import LimitedTestCase, s2b, skip_if_no_ssl

certificate_file = os.path.join(os.path.dirname(__file__), 'test_server.crt')
private_key_file = os.path.join(os.path.dirname(__file__), 'test_server.key')

class TestServe(LimitedTestCase):
    def setUp (self):
        super(TestServe, self).setUp()
        from evy import debug

        debug.hub_exceptions(False)

    def tearDown (self):
        super(TestServe, self).tearDown()
        from evy import debug

        debug.hub_exceptions(True)

    def test_exiting_server (self):
        # tests that the server closes the client sock on handle() exit
        def closer (sock, addr):
            pass

        l = evy.listen(('localhost', 0))
        gt = evy.spawn(evy.serve, l, closer)
        client = evy.connect(('localhost', l.getsockname()[1]))
        client.sendall(s2b('a'))
        self.assertFalse(client.recv(100))
        gt.kill()


    def test_excepting_server (self):
        # tests that the server closes the client sock on handle() exception
        def crasher (sock, addr):
            sock.recv(1024)
            0 // 0

        l = evy.listen(('localhost', 0))
        gt = evy.spawn(evy.serve, l, crasher)
        client = evy.connect(('localhost', l.getsockname()[1]))
        client.sendall(s2b('a'))
        self.assertRaises(ZeroDivisionError, gt.wait)
        self.assertFalse(client.recv(100))

    def test_excepting_server_already_closed (self):
        # same as above but with explicit clsoe before crash
        def crasher (sock, addr):
            sock.recv(1024)
            sock.close()
            0 // 0

        l = evy.listen(('localhost', 0))
        gt = evy.spawn(evy.serve, l, crasher)
        client = evy.connect(('localhost', l.getsockname()[1]))
        client.sendall(s2b('a'))
        self.assertRaises(ZeroDivisionError, gt.wait)
        self.assertFalse(client.recv(100))

    def test_called_for_each_connection (self):
        hits = [0]

        def counter (sock, addr):
            hits[0] += 1

        l = evy.listen(('localhost', 0))
        gt = evy.spawn(evy.serve, l, counter)
        for i in xrange(100):
            client = evy.connect(('localhost', l.getsockname()[1]))
            self.assertFalse(client.recv(100))
        gt.kill()
        self.assertEqual(100, hits[0])

    def test_blocking (self):
        l = evy.listen(('localhost', 0))
        x = evy.with_timeout(0.01,
                                  evy.serve, l, lambda c, a: None,
                                  timeout_value = "timeout")
        self.assertEqual(x, "timeout")

    def test_raising_stopserve (self):
        def stopit (conn, addr):
            raise evy.StopServe()

        l = evy.listen(('localhost', 0))
        # connect to trigger a call to stopit
        gt = evy.spawn(evy.connect,
            ('localhost', l.getsockname()[1]))
        evy.serve(l, stopit)
        gt.wait()

    def test_concurrency (self):
        evt = event.Event()

        def waiter (sock, addr):
            sock.sendall(s2b('hi'))
            evt.wait()

        l = evy.listen(('localhost', 0))
        gt = evy.spawn(evy.serve, l, waiter, 5)

        def test_client ():
            c = evy.connect(('localhost', l.getsockname()[1]))
            # verify the client is connected by getting data
            self.assertEquals(s2b('hi'), c.recv(2))
            return c

        clients = [test_client() for i in xrange(5)]
        # very next client should not get anything
        x = evy.with_timeout(0.01,
                                  test_client,
                                  timeout_value = "timed out")
        self.assertEquals(x, "timed out")

    @skip_if_no_ssl
    def test_wrap_ssl (self):
        server = evy.wrap_ssl(evy.listen(('localhost', 0)),
                                   certfile = certificate_file,
                                   keyfile = private_key_file, server_side = True)
        port = server.getsockname()[1]

        def handle (sock, addr):
            sock.sendall(sock.recv(1024))
            raise evy.StopServe()

        evy.spawn(evy.serve, server, handle)
        client = evy.wrap_ssl(evy.connect(('localhost', port)))
        client.sendall("echo")
        self.assertEquals("echo", client.recv(1024))

    def test_socket_reuse (self):
        lsock1 = evy.listen(('localhost', 0))
        port = lsock1.getsockname()[1]

        def same_socket ():
            return evy.listen(('localhost', port))

        self.assertRaises(socket.error, same_socket)
        lsock1.close()
        assert same_socket()

