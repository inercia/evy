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


import os
from tests.test_patcher import ProcessBase

class Socket(ProcessBase):
    def test_patched_thread (self):
        new_mod = """from evy.green import socket
socket.gethostbyname('localhost')
socket.getaddrinfo('localhost', 80)
"""
        os.environ['EVENTLET_TPOOL_DNS'] = 'yes'
        try:
            self.write_to_tempfile("newmod", new_mod)
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 1, lines)
        finally:
            del os.environ['EVENTLET_TPOOL_DNS']


class Tpool(ProcessBase):
    def test_tpool_size (self):
        expected = "40"
        normal = "20"
        new_mod = """from evy import tpool
import evy
import time
current = [0]
highwater = [0]
def count():
    current[0] += 1
    time.sleep(0.1)
    if current[0] > highwater[0]:
        highwater[0] = current[0]
    current[0] -= 1
expected = %s
normal = %s
p = evy.GreenPool()
for i in xrange(expected*2):
    p.spawn(tpool.execute, count)
p.waitall()
assert highwater[0] > 20, "Highwater %%s  <= %%s" %% (highwater[0], normal)
"""
        os.environ['EVENTLET_THREADPOOL_SIZE'] = expected
        try:
            self.write_to_tempfile("newmod", new_mod % (expected, normal))
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 1, lines)
        finally:
            del os.environ['EVENTLET_THREADPOOL_SIZE']

    def test_tpool_negative (self):
        new_mod = """from evy import tpool
import evy
import time
def do():
    print "should not get here"
try:
    tpool.execute(do)
except AssertionError:
    print "success"
"""
        os.environ['EVENTLET_THREADPOOL_SIZE'] = "-1"
        try:
            self.write_to_tempfile("newmod", new_mod)
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 2, lines)
            self.assertEqual(lines[0], "success", output)
        finally:
            del os.environ['EVENTLET_THREADPOOL_SIZE']

    def test_tpool_zero (self):
        new_mod = """from evy import tpool
import evy
import time
def do():
    print "ran it"
tpool.execute(do)
"""
        os.environ['EVENTLET_THREADPOOL_SIZE'] = "0"
        try:
            self.write_to_tempfile("newmod", new_mod)
            output, lines = self.launch_subprocess('newmod.py')
            self.assertEqual(len(lines), 4, lines)
            self.assertEqual(lines[-2], 'ran it', lines)
            self.assert_('Warning' in lines[1] or 'Warning' in lines[0], lines)
        finally:
            del os.environ['EVENTLET_THREADPOOL_SIZE']


class Hub(ProcessBase):
    def setUp (self):
        super(Hub, self).setUp()
        self.old_environ = os.environ.get('EVENTLET_HUB')
        os.environ['EVENTLET_HUB'] = 'selects'

    def tearDown (self):
        if self.old_environ:
            os.environ['EVENTLET_HUB'] = self.old_environ
        else:
            del os.environ['EVENTLET_HUB']
        super(Hub, self).tearDown()

    def test_evy_hub (self):
        new_mod = """from evy import hubs
print hubs.get_hub()
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 2, "\n".join(lines))
        self.assert_("selects" in lines[0])

