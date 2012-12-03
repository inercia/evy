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


"""
Test than modules in evy.green package are indeed green.
To do that spawn a green server and then access it using a green socket.
If either operation blocked the whole script would block and timeout.
"""

import unittest

from evy.green import urllib2, BaseHTTPServer
from evy.greenthread import spawn, kill

class QuietHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message (self, *args, **kw):
        pass


def start_http_server ():
    server_address = ('localhost', 0)
    httpd = BaseHTTPServer.HTTPServer(server_address, QuietHandler)
    sa = httpd.socket.getsockname()
    #print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.request_count = 0

    def serve ():
        # increment the request_count before handling the request because
        # the send() for the response blocks (or at least appeared to be)
        httpd.request_count += 1
        httpd.handle_request()

    return spawn(serve), httpd, sa[1]


class TestGreenness(unittest.TestCase):

    def setUp (self):
        self.gthread, self.server, self.port = start_http_server()
        #print 'Spawned the server'

    def tearDown (self):
        self.server.server_close()
        kill(self.gthread)

    def test_urllib2 (self):
        self.assertEqual(self.server.request_count, 0)
        try:
            urllib2.urlopen('http://127.0.0.1:%s' % self.port)
            assert False, 'should not get there'
        except urllib2.HTTPError, ex:
            assert ex.code == 501, repr(ex)
        self.assertEqual(self.server.request_count, 1)

if __name__ == '__main__':
    unittest.main()
