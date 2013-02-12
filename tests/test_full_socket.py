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

import unittest
from test import test_support

import errno
import traceback
import Queue
import sys
import array
import contextlib
from weakref import proxy
import signal
import math


from evy.patched import socket, select, time, os, thread, threading



def try_address (host, port = 0, family = socket.AF_INET):
    """Try to bind a socket on the given host:port and return True
    if that has been possible."""
    try:
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.bind((host, port))
    except (socket.error, socket.gaierror):
        return False
    else:
        sock.close()
        return True


HOST = test_support.HOST
MSG = b'Michael Gilfix was here\n'
SUPPORTS_IPV6 = socket.has_ipv6 and try_address('::1', family = socket.AF_INET6)


from tests import SocketConnectedTest, ThreadedTCPSocketTest, SocketPairTest, SocketTCPTest, ThreadableTest

#######################################################################
## Begin Tests



@unittest.skipUnless(thread, 'Threading required for this test.')
class BasicTCPTest(SocketConnectedTest):
    def __init__ (self, methodName = 'runTest'):
        SocketConnectedTest.__init__(self, methodName = methodName)

    def testRecv (self):
        # Testing large receive over TCP
        msg = self.cli_conn.recv(1024)
        self.assertEqual(msg, MSG)

    def _testRecv (self):
        self.serv_conn.send(MSG)

    def testOverFlowRecv (self):
        # Testing receive in chunks over TCP
        seg1 = self.cli_conn.recv(len(MSG) - 3)
        seg2 = self.cli_conn.recv(1024)
        msg = seg1 + seg2
        self.assertEqual(msg, MSG)

    def _testOverFlowRecv (self):
        self.serv_conn.send(MSG)

    def testRecvFrom (self):
        # Testing large recvfrom() over TCP
        msg, addr = self.cli_conn.recvfrom(1024)
        self.assertEqual(msg, MSG)

    def _testRecvFrom (self):
        self.serv_conn.send(MSG)

    def testOverFlowRecvFrom (self):
        # Testing recvfrom() in chunks over TCP
        seg1, addr = self.cli_conn.recvfrom(len(MSG) - 3)
        seg2, addr = self.cli_conn.recvfrom(1024)
        msg = seg1 + seg2
        self.assertEqual(msg, MSG)

    def _testOverFlowRecvFrom (self):
        self.serv_conn.send(MSG)

    def testSendAll (self):
        # Testing sendall() with a 2048 byte string over TCP
        msg = ''
        while 1:
            read = self.cli_conn.recv(1024)
            if not read:
                break
            msg += read
        self.assertEqual(msg, 'f' * 2048)

    def _testSendAll (self):
        big_chunk = 'f' * 2048
        self.serv_conn.sendall(big_chunk)

    def testFromFd (self):
        # Testing fromfd()
        if not hasattr(socket, "fromfd"):
            return # On Windows, this doesn't exist
        fd = self.cli_conn.fileno()
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(sock.close)
        msg = sock.recv(1024)
        self.assertEqual(msg, MSG)

    def _testFromFd (self):
        self.serv_conn.send(MSG)

    def testDup (self):
        # Testing dup()
        sock = self.cli_conn.dup()
        self.addCleanup(sock.close)
        msg = sock.recv(1024)
        self.assertEqual(msg, MSG)

    def _testDup (self):
        self.serv_conn.send(MSG)

    def testShutdown (self):
        # Testing shutdown()
        msg = self.cli_conn.recv(1024)
        self.assertEqual(msg, MSG)
        # wait for _testShutdown to finish: on OS X, when the server
        # closes the connection the client also becomes disconnected,
        # and the client's shutdown call will fail. (Issue #4397.)
        self.done.wait()

    def _testShutdown (self):
        self.serv_conn.send(MSG)
        self.serv_conn.shutdown(2)


@unittest.skipUnless(thread, 'Threading required for this test.')
class TCPCloserTest(ThreadedTCPSocketTest):
    def testClose (self):
        conn, addr = self.serv.accept()
        conn.close()

        sd = self.cli
        read, write, err = select.select([sd], [], [], 1.0)
        self.assertEqual(read, [sd])
        self.assertEqual(sd.recv(1), '')

    def _testClose (self):
        self.cli.connect((HOST, self.port))
        time.sleep(1.0)


@unittest.skipUnless(thread, 'Threading required for this test.')
class BasicSocketPairTest(SocketPairTest):
    def __init__ (self, methodName = 'runTest'):
        SocketPairTest.__init__(self, methodName = methodName)

    def testRecv (self):
        msg = self.serv.recv(1024)
        self.assertEqual(msg, MSG)

    def _testRecv (self):
        self.cli.send(MSG)

    def testSend (self):
        self.serv.send(MSG)

    def _testSend (self):
        msg = self.cli.recv(1024)
        self.assertEqual(msg, MSG)


@unittest.skipUnless(thread, 'Threading required for this test.')
class NonBlockingTCPTests(ThreadedTCPSocketTest):
    def __init__ (self, methodName = 'runTest'):
        ThreadedTCPSocketTest.__init__(self, methodName = methodName)

    def testSetBlocking (self):
        # Testing whether set blocking works
        self.serv.setblocking(0)
        start = time.time()
        try:
            self.serv.accept()
        except socket.error:
            pass
        end = time.time()
        self.assertTrue((end - start) < 1.0, "Error setting non-blocking mode.")

    def _testSetBlocking (self):
        pass

    def testAccept (self):
        # Testing non-blocking accept
        self.serv.setblocking(0)
        try:
            conn, addr = self.serv.accept()
        except socket.error:
            pass
        else:
            self.fail("Error trying to do non-blocking accept.")
        read, write, err = select.select([self.serv], [], [])
        if self.serv in read:
            conn, addr = self.serv.accept()
            conn.close()
        else:
            self.fail("Error trying to do accept after select.")

    def _testAccept (self):
        time.sleep(0.1)
        self.cli.connect((HOST, self.port))

    def testConnect (self):
        # Testing non-blocking connect
        conn, addr = self.serv.accept()
        conn.close()

    def _testConnect (self):
        self.cli.settimeout(10)
        self.cli.connect((HOST, self.port))

    def testRecv (self):
        # Testing non-blocking recv
        conn, addr = self.serv.accept()
        conn.setblocking(0)
        try:
            msg = conn.recv(len(MSG))
        except socket.error:
            pass
        else:
            self.fail("Error trying to do non-blocking recv.")
        read, write, err = select.select([conn], [], [])
        if conn in read:
            msg = conn.recv(len(MSG))
            conn.close()
            self.assertEqual(msg, MSG)
        else:
            self.fail("Error during select call to non-blocking socket.")

    def _testRecv (self):
        self.cli.connect((HOST, self.port))
        time.sleep(0.1)
        self.cli.send(MSG)



class NetworkConnectionTest(object):
    """Prove network connection."""

    def clientSetUp (self):
        # We're inherited below by BasicTCPTest2, which also inherits
        # BasicTCPTest, which defines self.port referenced below.
        self.cli = socket.create_connection((HOST, self.port))
        self.serv_conn = self.cli


class BasicTCPTest2(NetworkConnectionTest, BasicTCPTest):
    """Tests that NetworkConnection does not break existing TCP functionality.
    """


class NetworkConnectionNoServer(unittest.TestCase):
    class MockSocket(socket.socket):
        def connect (self, *args):
            raise socket.timeout('timed out')

    @contextlib.contextmanager
    def mocked_socket_module (self):
        """Return a socket which times out on connect"""
        old_socket = socket.socket
        socket.socket = self.MockSocket
        try:
            yield
        finally:
            socket.socket = old_socket

    def test_connect (self):
        port = test_support.find_unused_port()
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(cli.close)
        with self.assertRaises(socket.error) as cm:
            cli.connect((HOST, port))
        self.assertEqual(cm.exception.errno, errno.ECONNREFUSED)

    def test_create_connection (self):
        # Issue #9792: errors raised by create_connection() should have
        # a proper errno attribute.
        port = test_support.find_unused_port()
        with self.assertRaises(socket.error) as cm:
            socket.create_connection((HOST, port))
        self.assertEqual(cm.exception.errno, errno.ECONNREFUSED)

    def test_create_connection_timeout (self):
        # Issue #9792: create_connection() should not recast timeout errors
        # as generic socket errors.
        with self.mocked_socket_module():
            with self.assertRaises(socket.timeout):
                socket.create_connection((HOST, 1234))


@unittest.skipUnless(thread, 'Threading required for this test.')
class NetworkConnectionAttributesTest(SocketTCPTest, ThreadableTest):
    def __init__ (self, methodName = 'runTest'):
        SocketTCPTest.__init__(self, methodName = methodName)
        ThreadableTest.__init__(self)

    def clientSetUp (self):
        self.source_port = test_support.find_unused_port()

    def clientTearDown (self):
        self.cli.close()
        self.cli = None
        ThreadableTest.clientTearDown(self)

    def _justAccept (self):
        conn, addr = self.serv.accept()
        conn.close()

    testFamily = _justAccept

    def _testFamily (self):
        self.cli = socket.create_connection((HOST, self.port), timeout = 30)
        self.addCleanup(self.cli.close)
        self.assertEqual(self.cli.family, 2)

    testSourceAddress = _justAccept

    def _testSourceAddress (self):
        self.cli = socket.create_connection((HOST, self.port), timeout = 30,
                                            source_address = ('', self.source_port))
        self.addCleanup(self.cli.close)
        self.assertEqual(self.cli.getsockname()[1], self.source_port)
        # The port number being used is sufficient to show that the bind()
        # call happened.

    testTimeoutDefault = _justAccept

    def _testTimeoutDefault (self):
        # passing no explicit timeout uses socket's global default
        self.assertTrue(socket.getdefaulttimeout() is None)
        socket.setdefaulttimeout(42)
        try:
            self.cli = socket.create_connection((HOST, self.port))
            self.addCleanup(self.cli.close)
        finally:
            socket.setdefaulttimeout(None)
        self.assertEqual(self.cli.gettimeout(), 42)

    testTimeoutNone = _justAccept

    def _testTimeoutNone (self):
        # None timeout means the same as sock.settimeout(None)
        self.assertTrue(socket.getdefaulttimeout() is None)
        socket.setdefaulttimeout(30)
        try:
            self.cli = socket.create_connection((HOST, self.port), timeout = None)
            self.addCleanup(self.cli.close)
        finally:
            socket.setdefaulttimeout(None)
        self.assertEqual(self.cli.gettimeout(), None)

    testTimeoutValueNamed = _justAccept

    def _testTimeoutValueNamed (self):
        self.cli = socket.create_connection((HOST, self.port), timeout = 30)
        self.assertEqual(self.cli.gettimeout(), 30)

    testTimeoutValueNonamed = _justAccept

    def _testTimeoutValueNonamed (self):
        self.cli = socket.create_connection((HOST, self.port), 30)
        self.addCleanup(self.cli.close)
        self.assertEqual(self.cli.gettimeout(), 30)


@unittest.skipUnless(thread, 'Threading required for this test.')
class NetworkConnectionBehaviourTest(SocketTCPTest, ThreadableTest):
    def __init__ (self, methodName = 'runTest'):
        SocketTCPTest.__init__(self, methodName = methodName)
        ThreadableTest.__init__(self)

    def clientSetUp (self):
        pass

    def clientTearDown (self):
        self.cli.close()
        self.cli = None
        ThreadableTest.clientTearDown(self)

    def testInsideTimeout (self):
        conn, addr = self.serv.accept()
        self.addCleanup(conn.close)
        time.sleep(3)
        conn.send("done!")

    testOutsideTimeout = testInsideTimeout

    def _testInsideTimeout (self):
        self.cli = sock = socket.create_connection((HOST, self.port))
        data = sock.recv(5)
        self.assertEqual(data, "done!")

    def _testOutsideTimeout (self):
        self.cli = sock = socket.create_connection((HOST, self.port), timeout = 1)
        self.assertRaises(socket.timeout, lambda: sock.recv(5))


class TCPTimeoutTest(SocketTCPTest):
    def testTCPTimeout (self):
        def raise_timeout (*args, **kwargs):
            self.serv.settimeout(1.0)
            self.serv.accept()

        self.assertRaises(socket.timeout, raise_timeout,
                          "Error generating a timeout exception (TCP)")

    def testTimeoutZero (self):
        ok = False
        try:
            self.serv.settimeout(0.0)
            foo = self.serv.accept()
        except socket.timeout:
            self.fail("caught timeout instead of error (TCP)")
        except socket.error:
            ok = True
        except:
            self.fail("caught unexpected exception (TCP)")
        if not ok:
            self.fail("accept() returned success when we did not expect it")

    def testInterruptedTimeout (self):
        # XXX I don't know how to do this test on MSWindows or any other
        # plaform that doesn't support signal.alarm() or os.kill(), though
        # the bug should have existed on all platforms.
        if not hasattr(signal, "alarm"):
            return # can only test on *nix
        self.serv.settimeout(5.0)   # must be longer than alarm

        class Alarm(Exception):
            pass

        def alarm_handler (signal, frame):
            raise Alarm

        old_alarm = signal.signal(signal.SIGALRM, alarm_handler)
        try:
            signal.alarm(2)    # POSIX allows alarm to be up to 1 second early
            try:
                foo = self.serv.accept()
            except socket.timeout:
                self.fail("caught timeout instead of Alarm")
            except Alarm:
                pass
            except:
                self.fail("caught other exception instead of Alarm:"
                          " %s(%s):\n%s" %
                          (sys.exc_info()[:2] + (traceback.format_exc(),)))
            else:
                self.fail("nothing caught")
            finally:
                signal.alarm(0)         # shut off alarm
        except Alarm:
            self.fail("got Alarm in wrong place")
        finally:
            # no alarm can be pending.  Safe to restore old handler.
            signal.signal(signal.SIGALRM, old_alarm)



class TestExceptions(unittest.TestCase):
    def testExceptionTree (self):
        self.assertTrue(issubclass(socket.error, Exception))
        self.assertTrue(issubclass(socket.herror, socket.error))
        self.assertTrue(issubclass(socket.gaierror, socket.error))
        self.assertTrue(issubclass(socket.timeout, socket.error))


class TestLinuxAbstractNamespace(unittest.TestCase):
    UNIX_PATH_MAX = 108

    def testLinuxAbstractNamespace (self):
        address = "\x00python-test-hello\x00\xff"
        s1 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s1.bind(address)
        s1.listen(1)
        s2 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s2.connect(s1.getsockname())
        s1.accept()
        self.assertEqual(s1.getsockname(), address)
        self.assertEqual(s2.getpeername(), address)

    def testMaxName (self):
        address = "\x00" + "h" * (self.UNIX_PATH_MAX - 1)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(address)
        self.assertEqual(s.getsockname(), address)

    def testNameOverflow (self):
        address = "\x00" + "h" * self.UNIX_PATH_MAX
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.assertRaises(socket.error, s.bind, address)


@unittest.skipUnless(thread, 'Threading required for this test.')
class BufferIOTest(SocketConnectedTest):
    """
    Test the buffer versions of socket.recv() and socket.send().
    """

    def __init__ (self, methodName = 'runTest'):
        SocketConnectedTest.__init__(self, methodName = methodName)

    def testRecvIntoArray (self):
        buf = array.array('c', ' ' * 1024)
        nbytes = self.cli_conn.recv_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf.tostring()[:len(MSG)]
        self.assertEqual(msg, MSG)

    def _testRecvIntoArray (self):
        with test_support.check_py3k_warnings():
            buf = buffer(MSG)
        self.serv_conn.send(buf)

    def testRecvIntoBytearray (self):
        buf = bytearray(1024)
        nbytes = self.cli_conn.recv_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _testRecvIntoBytearray = _testRecvIntoArray

    def testRecvIntoMemoryview (self):
        buf = bytearray(1024)
        nbytes = self.cli_conn.recv_into(memoryview(buf))
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _testRecvIntoMemoryview = _testRecvIntoArray

    def testRecvFromIntoArray (self):
        buf = array.array('c', ' ' * 1024)
        nbytes, addr = self.cli_conn.recvfrom_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf.tostring()[:len(MSG)]
        self.assertEqual(msg, MSG)

    def _testRecvFromIntoArray (self):
        with test_support.check_py3k_warnings():
            buf = buffer(MSG)
        self.serv_conn.send(buf)

    def testRecvFromIntoBytearray (self):
        buf = bytearray(1024)
        nbytes, addr = self.cli_conn.recvfrom_into(buf)
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _testRecvFromIntoBytearray = _testRecvFromIntoArray

    def testRecvFromIntoMemoryview (self):
        buf = bytearray(1024)
        nbytes, addr = self.cli_conn.recvfrom_into(memoryview(buf))
        self.assertEqual(nbytes, len(MSG))
        msg = buf[:len(MSG)]
        self.assertEqual(msg, MSG)

    _testRecvFromIntoMemoryview = _testRecvFromIntoArray


TIPC_STYPE = 2000
TIPC_LOWER = 200
TIPC_UPPER = 210


def isTipcAvailable ():
    """Check if the TIPC module is loaded

    The TIPC module is not loaded automatically on Ubuntu and probably
    other Linux distros.
    """
    if not hasattr(socket, "AF_TIPC"):
        return False
    if not os.path.isfile("/proc/modules"):
        return False
    with open("/proc/modules") as f:
        for line in f:
            if line.startswith("tipc "):
                return True
    if test_support.verbose:
        print "TIPC module is not loaded, please 'sudo modprobe tipc'"
    return False


class TIPCTest(unittest.TestCase):
    @unittest.skip
    def testRDM (self):
        srv = socket.socket(socket.AF_TIPC, socket.SOCK_RDM)
        cli = socket.socket(socket.AF_TIPC, socket.SOCK_RDM)

        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srvaddr = (socket.TIPC_ADDR_NAMESEQ, TIPC_STYPE,
                   TIPC_LOWER, TIPC_UPPER)
        srv.bind(srvaddr)

        sendaddr = (socket.TIPC_ADDR_NAME, TIPC_STYPE,
                    TIPC_LOWER + (TIPC_UPPER - TIPC_LOWER) / 2, 0)
        cli.sendto(MSG, sendaddr)

        msg, recvaddr = srv.recvfrom(1024)

        self.assertEqual(cli.getsockname(), recvaddr)
        self.assertEqual(msg, MSG)


class TIPCThreadableTest(unittest.TestCase, ThreadableTest):
    def __init__ (self, methodName = 'runTest'):
        unittest.TestCase.__init__(self, methodName = methodName)
        ThreadableTest.__init__(self)

    def setUp (self):
        self.srv = socket.socket(socket.AF_TIPC, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srvaddr = (socket.TIPC_ADDR_NAMESEQ, TIPC_STYPE,
                   TIPC_LOWER, TIPC_UPPER)
        self.srv.bind(srvaddr)
        self.srv.listen(5)
        self.serverExplicitReady()
        self.conn, self.connaddr = self.srv.accept()

    def clientSetUp (self):
        # The is a hittable race between serverExplicitReady() and the
        # accept() call; sleep a little while to avoid it, otherwise
        # we could get an exception
        time.sleep(0.1)
        self.cli = socket.socket(socket.AF_TIPC, socket.SOCK_STREAM)
        addr = (socket.TIPC_ADDR_NAME, TIPC_STYPE,
                TIPC_LOWER + (TIPC_UPPER - TIPC_LOWER) / 2, 0)
        self.cli.connect(addr)
        self.cliaddr = self.cli.getsockname()

    @unittest.skip
    def testStream (self):
        msg = self.conn.recv(1024)
        self.assertEqual(msg, MSG)
        self.assertEqual(self.cliaddr, self.connaddr)

    def _testStream (self):
        self.cli.send(MSG)
        self.cli.close()

