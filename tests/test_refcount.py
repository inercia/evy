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


"""This test checks that socket instances (not GreenSockets but underlying sockets)
are not leaked by the hub.
"""

import unittest
import weakref
import gc

from pprint import pformat

from evy.support import clear_sys_exc_info
from evy.patched import socket
from evy.patched.thread import start_new_thread
from evy.patched.time import sleep


SOCKET_TIMEOUT = 0.1


def init_server ():
    s = socket.socket()
    s.settimeout(SOCKET_TIMEOUT)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('localhost', 0))
    s.listen(5)
    return s, s.getsockname()[1]


def handle_request (s, raise_on_timeout):
    try:
        conn, address = s.accept()
    except socket.timeout:
        if raise_on_timeout:
            raise
        else:
            return
            #print 'handle_request - accepted'
    res = conn.recv(100)
    assert res == 'hello', repr(res)
    #print 'handle_request - recvd %r' % res
    res = conn.send('bye')
    #print 'handle_request - sent %r' % res
    #print 'handle_request - conn refcount: %s' % sys.getrefcount(conn)
    #conn.close()


def make_request (port):
    #print 'make_request'
    s = socket.socket()
    s.connect(('localhost', port))
    #print 'make_request - connected'
    res = s.send('hello')
    #print 'make_request - sent %s' % res
    res = s.recv(100)
    assert res == 'bye', repr(res)
    #print 'make_request - recvd %r' % res
    #s.close()


def run_interaction (run_client):
    s, port = init_server()
    start_new_thread(handle_request, (s, run_client))
    if run_client:
        start_new_thread(make_request, (port,))
    sleep(0.1 + SOCKET_TIMEOUT)
    #print sys.getrefcount(s.fd)
    #s.close()
    return weakref.ref(s.fd)


def run_and_check (run_client):
    w = run_interaction(run_client = run_client)
    clear_sys_exc_info()
    if w():
        print pformat(gc.get_referrers(w()))
        for x in gc.get_referrers(w()):
            print pformat(x)
            for y in gc.get_referrers(x):
                print '-', pformat(y)
        raise AssertionError('server should be dead by now')


def test_clean_exit ():
    run_and_check(True)
    run_and_check(True)


def test_timeout_exit ():
    run_and_check(False)
    run_and_check(False)


if __name__ == '__main__':
    unittest.main()

