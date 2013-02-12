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

import Queue

from evy.patched import socket, thread, threading



HOST = test_support.HOST
MSG = b'Michael Gilfix was here\n'




class SocketUDPTest(unittest.TestCase):
    def setUp (self):
        self.serv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = test_support.bind_port(self.serv)

    def tearDown (self):
        self.serv.close()
        self.serv = None


class ThreadableTest:
    """Threadable Test class

    The ThreadableTest class makes it easy to create a threaded
    client/server pair from an existing unit test. To create a
    new threaded class from an existing unit test, use multiple
    inheritance:

        class NewClass (OldClass, ThreadableTest):
            pass

    This class defines two new fixture functions with obvious
    purposes for overriding:

        clientSetUp ()
        clientTearDown ()

    Any new test functions within the class must then define
    tests in pairs, where the test name is preceeded with a
    '_' to indicate the client portion of the test. Ex:

        def testFoo(self):
            # Server portion

        def _testFoo(self):
            # Client portion

    Any exceptions raised by the clients during their tests
    are caught and transferred to the main thread to alert
    the testing framework.

    Note, the server setup function cannot call any blocking
    functions that rely on the client thread during setup,
    unless serverExplicitReady() is called just before
    the blocking call (such as in setting up a client/server
    connection and performing the accept() in setUp().
    """

    def __init__ (self):
        # Swap the true setup function
        self.__setUp = self.setUp
        self.__tearDown = self.tearDown
        self.setUp = self._setUp
        self.tearDown = self._tearDown

    def serverExplicitReady (self):
        """This method allows the server to explicitly indicate that
        it wants the client thread to proceed. This is useful if the
        server is about to execute a blocking routine that is
        dependent upon the client thread during its setup routine."""
        self.server_ready.set()

    def _setUp (self):
        self.server_ready = threading.Event()
        self.client_ready = threading.Event()
        self.done = threading.Event()
        self.queue = Queue.Queue(1)

        # Do some munging to start the client test.
        methodname = self.id()
        i = methodname.rfind('.')
        methodname = methodname[i + 1:]
        test_method = getattr(self, '_' + methodname)
        self.client_thread = thread.start_new_thread(
            self.clientRun, (test_method,))

        self.__setUp()
        if not self.server_ready.is_set():
            self.server_ready.set()
        self.client_ready.wait()

    def _tearDown (self):
        self.__tearDown()
        self.done.wait()

        if not self.queue.empty():
            msg = self.queue.get()
            self.fail(msg)

    def clientRun (self, test_func):
        self.server_ready.wait()
        self.clientSetUp()
        self.client_ready.set()
        if not callable(test_func):
            raise TypeError("test_func must be a callable function.")
        try:
            test_func()
        except Exception, strerror:
            self.queue.put(strerror)
        self.clientTearDown()

    def clientSetUp (self):
        raise NotImplementedError("clientSetUp must be implemented.")

    def clientTearDown (self):
        self.done.set()
        thread.exit()



#######################################################################
## Begin Tests


class ThreadedUDPSocketTest(SocketUDPTest, ThreadableTest):
    def __init__ (self, methodName = 'runTest'):
        SocketUDPTest.__init__(self, methodName = methodName)
        ThreadableTest.__init__(self)

    def clientSetUp (self):
        self.cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def clientTearDown (self):
        self.cli.close()
        self.cli = None
        ThreadableTest.clientTearDown(self)


@unittest.skipUnless(thread, 'Threading required for this test.')
class BasicUDPTest(ThreadedUDPSocketTest):
    def __init__ (self, methodName = 'runTest'):
        ThreadedUDPSocketTest.__init__(self, methodName = methodName)

    def testSendtoAndRecv (self):
        # Testing sendto() and Recv() over UDP
        msg = self.serv.recv(len(MSG))
        self.assertEqual(msg, MSG)

    def _testSendtoAndRecv (self):
        self.cli.sendto(MSG, 0, (HOST, self.port))

    def testRecvFrom (self):
        # Testing recvfrom() over UDP
        msg, addr = self.serv.recvfrom(len(MSG))
        self.assertEqual(msg, MSG)

    def _testRecvFrom (self):
        self.cli.sendto(MSG, 0, (HOST, self.port))

    def testRecvFromNegative (self):
        # Negative lengths passed to recvfrom should give ValueError.
        self.assertRaises(ValueError, self.serv.recvfrom, -1)

    def _testRecvFromNegative (self):
        self.cli.sendto(MSG, 0, (HOST, self.port))



class UDPTimeoutTest(SocketUDPTest):
    def testUDPTimeout (self):
        def raise_timeout (*args, **kwargs):
            self.serv.settimeout(1.0)
            self.serv.recv(1024)

        self.assertRaises(socket.timeout, raise_timeout,
                          "Error generating a timeout exception (UDP)")

    def testTimeoutZero (self):
        ok = False
        try:
            self.serv.settimeout(0.0)
            foo = self.serv.recv(1024)
        except socket.timeout:
            self.fail("caught timeout instead of error (UDP)")
        except socket.error:
            ok = True
        except:
            self.fail("caught unexpected exception (UDP)")
        if not ok:
            self.fail("recv() returned success when we did not expect it")


