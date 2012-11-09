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
import socket as _original_sock
from evy import api
from evy.green import socket

class TestSocketErrors(unittest.TestCase):
    def test_connection_refused (self):
        # open and close a dummy server to find an unused port
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        port = server.getsockname()[1]
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

    def test_timeout_real_socket (self):
        """ Test underlying socket behavior to ensure correspondence
            between green sockets and the underlying socket module. """
        return self.test_timeout(socket = _original_sock)

    def test_timeout (self, socket = socket):
        """ Test that the socket timeout exception works correctly. """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        port = server.getsockname()[1]

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
    unittest.main()
