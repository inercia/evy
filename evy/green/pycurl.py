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
PyCCurl monkey patching
"""


## TODO: this code is not functional!!!


import evy
from evy import patcher
from evy.support import greenlets as greenlet

__patched__ = ['get']
pycurl_orig = __import__("pycurl")




CURL_POLL_NONE = 0
CURL_POLL_IN = 1
CURL_POLL_OUT = 2
CURL_POLL_INOUT = 3
CURL_POLL_REMOVE = 4



SUSPENDED_COROS = {}
LAST_SOCKET = None
LAST_SOCKET_DONE = False


def hub_callback(fileno):
    print "HUB_CALLBACK", fileno
    SUSPENDED_COROS[fileno].switch()


def socket_callback(action, socket, user_data, socket_data):
    global LAST_SOCKET
    global LAST_SOCKET_DONE
    LAST_SOCKET = socket
    LAST_SOCKET_DONE = False
    print "SOCKET_CALLBACK", action, socket, user_data, socket_data
    hub = evy.hubs.get_hub()
    if action == CURL_POLL_NONE:
        # nothing to do
        return
    elif action == CURL_POLL_IN:
        print "POLLIN"
        hub.add_descriptor(socket, read=hub_callback)
    elif action == CURL_POLL_OUT:
        print "POLLOUT"
        hub.add_descriptor(socket, write=hub_callback)
    elif action == CURL_POLL_INOUT:
        print "POLLINOUT"
        hub.add_descriptor(socket, read=hub_callback, write=hub_callback)
    elif action == CURL_POLL_REMOVE:
        print "POLLREMOVE"
        hub.remove_descriptor(socket)
        LAST_SOCKET_DONE = True


THE_MULTI = pycurl_orig.CurlMulti()
THE_MULTI.setopt(pycurl_orig.M_SOCKETFUNCTION, socket_callback)


def read(*data):
    print "READ", data


def write(*data):
    print "WRITE", data


def runloop_observer(*_):
    result, numhandles = THE_MULTI.socket_all()
    print "PERFORM RESULT", result
    while result == pycurl_orig.E_CALL_MULTI_PERFORM:
        result, numhandles = THE_MULTI.socket_all()
        print "PERFORM RESULT2", result


def get(url):
    hub = evy.hubs.get_hub()
    c = pycurl_orig.Curl()
    c.setopt(pycurl_orig.URL, url)
    #c.setopt(pycurl.M_SOCKETFUNCTION, socket_callback)
    c.setopt(pycurl_orig.WRITEFUNCTION, write)
    c.setopt(pycurl_orig.READFUNCTION, read)
    c.setopt(pycurl_orig.NOSIGNAL, 1)
    THE_MULTI.add_handle(c)
    hub.add_observer(runloop_observer, 'before_waiting')
    while True:
        print "TOP"
        result, numhandles = THE_MULTI.socket_all()
        print "PERFORM RESULT", result
        while result == pycurl_orig.E_CALL_MULTI_PERFORM:
            result, numhandles = THE_MULTI.socket_all()
            print "PERFORM RESULT2", result

        if LAST_SOCKET_DONE:
            break

        SUSPENDED_COROS[LAST_SOCKET] = greenlet.getcurrent()
        print "SUSPENDED", SUSPENDED_COROS
        evy.hubs.get_hub().switch()
        print "BOTTOM"

    if not SUSPENDED_COROS:
        hub.remove_observer(runloop_observer)


#from eventlet.support import pycurls
#reload(pycurls); from eventlet.support import pycurls; pycurls.get('http://localhost/')


del patcher
