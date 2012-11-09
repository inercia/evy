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


import sys
import warnings
from tests import LimitedTestCase, main, skip_on_windows

warnings.simplefilter('ignore', DeprecationWarning)
from evy import processes, api

warnings.simplefilter('default', DeprecationWarning)

class TestEchoPool(LimitedTestCase):
    def setUp (self):
        super(TestEchoPool, self).setUp()
        self.pool = processes.ProcessPool('echo', ["hello"])

    @skip_on_windows
    def test_echo (self):
        result = None

        proc = self.pool.get()
        try:
            result = proc.read()
        finally:
            self.pool.put(proc)
        self.assertEquals(result, 'hello\n')

    @skip_on_windows
    def test_read_eof (self):
        proc = self.pool.get()
        try:
            proc.read()
            self.assertRaises(processes.DeadProcess, proc.read)
        finally:
            self.pool.put(proc)

    @skip_on_windows
    def test_empty_echo (self):
        p = processes.Process('echo', ['-n'])
        self.assertEquals('', p.read())
        self.assertRaises(processes.DeadProcess, p.read)


class TestCatPool(LimitedTestCase):
    def setUp (self):
        super(TestCatPool, self).setUp()
        api.sleep(0)
        self.pool = processes.ProcessPool('cat')

    @skip_on_windows
    def test_cat (self):
        result = None

        proc = self.pool.get()
        try:
            proc.write('goodbye')
            proc.close_stdin()
            result = proc.read()
        finally:
            self.pool.put(proc)

        self.assertEquals(result, 'goodbye')

    @skip_on_windows
    def test_write_to_dead (self):
        result = None

        proc = self.pool.get()
        try:
            proc.write('goodbye')
            proc.close_stdin()
            result = proc.read()
            self.assertRaises(processes.DeadProcess, proc.write, 'foo')
        finally:
            self.pool.put(proc)

    @skip_on_windows
    def test_close (self):
        result = None

        proc = self.pool.get()
        try:
            proc.write('hello')
            proc.close()
            self.assertRaises(processes.DeadProcess, proc.write, 'goodbye')
        finally:
            self.pool.put(proc)


class TestDyingProcessesLeavePool(LimitedTestCase):
    def setUp (self):
        super(TestDyingProcessesLeavePool, self).setUp()
        self.pool = processes.ProcessPool('echo', ['hello'], max_size = 1)

    @skip_on_windows
    def test_dead_process_not_inserted_into_pool (self):
        proc = self.pool.get()
        try:
            try:
                result = proc.read()
                self.assertEquals(result, 'hello\n')
                result = proc.read()
            except processes.DeadProcess:
                pass
        finally:
            self.pool.put(proc)
        proc2 = self.pool.get()
        self.assert_(proc is not proc2)


if __name__ == '__main__':
    main()
