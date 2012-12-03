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

import socket as _orig_sock
from tests import LimitedTestCase, main, skipped, s2b, skip_on_windows

from evy.green import socket

import errno

import os
import sys
import array
import tempfile, shutil

import unittest

from evy.dns import resolve


HOST = 'localhost'


class TestDnsResolution(unittest.TestCase):

    def test_resolve(self):
        res = resolve('google.com')
        self.assertTrue(len(res) > 1)

    def test_resolve_with_wrong_name(self):
        self.assertRaises(socket.gaierror, resolve('mipuroch.coocoo'))

    def testHostnameRes(self):

        # Testing hostname resolution mechanisms
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
        except socket.error:
            # Probably name lookup wasn't set up right; skip this test
            return
        self.assertTrue(ip.find('.') >= 0, "Error resolving host to ip.")
        try:
            hname, aliases, ipaddrs = socket.gethostbyaddr(ip)
        except socket.error:
            # Probably a similar problem as above; skip this test
            return
        all_host_names = [hostname, hname] + aliases
        fqhn = socket.getfqdn(ip)
        if not fqhn in all_host_names:
            self.fail("Error testing host resolution mechanisms. (fqdn: %s, all: %s)" % (fqhn, repr(all_host_names)))

    def test_ref_count_getnameinfo(self):
        if hasattr(sys, "getrefcount"):
            try:
                # On some versions, this loses a reference
                orig = sys.getrefcount(__name__)
                socket.getnameinfo(__name__,0)
            except TypeError:
                self.assertEqual(sys.getrefcount(__name__), orig, "socket.getnameinfo loses a reference")

    def test_interpreter_crash(self):
        # Making sure getnameinfo doesn't crash the interpreter
        try:
            # On some versions, this crashes the interpreter.
            socket.getnameinfo(('x', 0, 0, 0), 0)
        except socket.error:
            pass

    def test_gethostbyname(self):
        socket.gethostbyname('www.google.com')

    def test_getaddrinfo(self):
        try:
            socket.getaddrinfo('localhost', 80)
        except socket.gaierror as err:
            if err.errno == socket.EAI_SERVICE:
                # see http://bugs.python.org/issue1282647
                self.skipTest("buggy libc version")
            raise
            # len of every sequence is supposed to be == 5

        for info in socket.getaddrinfo(HOST, None):
            self.assertEqual(len(info), 5)
            # host can be a domain name, a string representation of an

        # IPv4/v6 address or None
        socket.getaddrinfo('localhost', 80)
        socket.getaddrinfo('127.0.0.1', 80)
        socket.getaddrinfo(None, 80)

        #if SUPPORTS_IPV6:
        #    socket.getaddrinfo('::1', 80)
        #    # port can be a string service name such as "http", a numeric

        # port number or None
        socket.getaddrinfo(HOST, "http")
        socket.getaddrinfo(HOST, 80)
        socket.getaddrinfo(HOST, None)

        # test family and socktype filters
        infos = socket.getaddrinfo(HOST, None, socket.AF_INET)
        for family, _, _, _, _ in infos:
            self.assertEqual(family, socket.AF_INET)
        infos = socket.getaddrinfo(HOST, None, 0, socket.SOCK_STREAM)
        for _, socktype, _, _, _ in infos:
            self.assertEqual(socktype, socket.SOCK_STREAM)
            # test proto and flags arguments

        socket.getaddrinfo(HOST, None, 0, 0, socket.SOL_TCP)
        socket.getaddrinfo(HOST, None, 0, 0, 0, socket.AI_PASSIVE)

        # a server willing to support both IPv4 and IPv6 will
        # usually do this
        socket.getaddrinfo(None, 0, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)


    def test_getnameinfo(self):
        addr, service = socket.getnameinfo(('127.0.0.1', 80), 0)
        self.assertEquals(service, 'http')

