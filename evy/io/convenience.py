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


import sys

from evy import greenthread
from evy import greenpool
from evy.green import socket
from evy.support import greenlets as greenlet


def connect (addr, family = socket.AF_INET, bind = None):
    """
    Convenience function for opening client sockets.

    :param addr: Address of the server to connect to.  For TCP sockets, this is a (host, port) tuple.
    :param family: Socket family, optional.  See :mod:`socket` documentation for available families.
    :param bind: Local address to bind to, optional.
    :return: The connected green socket object.
    """
    sock = socket.socket(family, socket.SOCK_STREAM)
    if bind is not None:
        sock.bind(bind)
    sock.connect(addr)
    return sock


def listen (addr, family = socket.AF_INET, backlog = 50):
    """
    Convenience function for opening server sockets.  This
    socket can be used in :func:`~evy.serve` or a custom ``accept()`` loop.

    Sets SO_REUSEADDR on the socket to save on annoyance. 

    :param addr: Address to listen on.  For TCP sockets, this is a (host, port)  tuple.
    :param family: Socket family, optional.  See :mod:`socket` documentation for available families.
    :param backlog: The maximum number of queued connections. Should be at least 1; the maximum value is system-dependent.
    :return: The listening green socket object.
    """
    sock = socket.socket(family, socket.SOCK_STREAM)
    if sys.platform[:3] != "win":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(addr)
    sock.listen(backlog)
    return sock


class StopServe(Exception):
    """
    Exception class used for quitting :func:`~evy.serve` gracefully."""
    pass


def _stop_checker (t, server_gt, conn):
    try:
        try:
            t.wait()
        finally:
            conn.close()
    except greenlet.GreenletExit:
        pass
    except Exception:
        greenthread.kill(server_gt, *sys.exc_info())


def serve (sock, handle, concurrency = 1000):
    """
    Runs a server on the supplied socket.  Calls the function *handle* in a
    separate greenthread for every incoming client connection.  *handle* takes
    two arguments: the client socket object, and the client address::
        
        def myhandle(client_sock, client_addr):
            print "client connected", client_addr
        
        evy.serve(evy.listen(('127.0.0.1', 9999)), myhandle)
        
    Returning from *handle* closes the client socket.
     
    :func:`serve` blocks the calling greenthread; it won't return until 
    the server completes.  If you desire an immediate return,
    spawn a new greenthread for :func:`serve`.
      
    Any uncaught exceptions raised in *handle* are raised as exceptions 
    from :func:`serve`, terminating the server, so be sure to be aware of the 
    exceptions your application can raise.  The return value of *handle* is 
    ignored.      
      
    Raise a :class:`~evy.StopServe` exception to gracefully terminate the 
    server -- that's the only way to get the server() function to return rather 
    than raise.

    The value in *concurrency* controls the maximum number of
    greenthreads that will be open at any time handling requests.  When
    the server hits the concurrency limit, it stops accepting new
    connections until the existing ones complete.
    """
    pool = greenpool.GreenPool(concurrency)
    server_gt = greenthread.getcurrent()

    while True:
        try:
            conn, addr = sock.accept()
            gt = pool.spawn(handle, conn, addr)
            gt.link(_stop_checker, server_gt, conn)
            conn, addr, gt = None, None, None
        except StopServe:
            return
