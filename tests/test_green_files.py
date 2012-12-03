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


from tests import LimitedTestCase, main, skip_on_windows

from evy.io.files import GreenFile
from evy.greenthread import spawn, sleep

import os
import tempfile, shutil



class TestGreenFiles(LimitedTestCase):

    @skip_on_windows
    def setUp (self):
        super(self.__class__, self).setUp()
        self.tempdir = tempfile.mkdtemp('_green_pipe_test')

    def tearDown (self):
        shutil.rmtree(self.tempdir)
        super(self.__class__, self).tearDown()

    def test_pipe (self):
        r, w = os.pipe()
        rf = GreenFile(r, 'r');
        wf = GreenFile(w, 'w', 0);

        def sender (f, content):
            for ch in content:
                sleep(0.0001)
                f.write(ch)
            f.close()

        one_line = "12345\n";
        spawn(sender, wf, one_line * 5)
        for i in xrange(5):
            line = rf.readline()
            sleep(0.01)
            self.assertEquals(line, one_line)
        self.assertEquals(rf.readline(), '')

    def test_pipe_read (self):
        # ensure that 'readline' works properly on GreenPipes when data is not
        # immediately available (fd is nonblocking, was raising EAGAIN)
        # also ensures that readline() terminates on '\n' and '\r\n'
        r, w = os.pipe()

        r = GreenFile(r)
        w = GreenFile(w, 'w')

        def writer ():
            sleep(.1)

            w.write('line\n')
            w.flush()

            w.write('line\r\n')
            w.flush()

        gt = spawn(writer)

        sleep(0)

        line = r.readline()
        self.assertEquals(line, 'line\n')

        line = r.readline()
        self.assertEquals(line, 'line\r\n')

        gt.wait()

    def test_pipe_writes_large_messages (self):
        r, w = os.pipe()

        r = GreenFile(r)
        w = GreenFile(w, 'w')

        large_message = "".join([1024 * chr(i) for i in xrange(65)])

        def writer ():
            w.write(large_message)
            w.close()

        gt = spawn(writer)

        for i in xrange(65):
            buf = r.read(1024)
            expected = 1024 * chr(i)
            self.assertEquals(buf, expected,
                              "expected=%r..%r, found=%r..%r iter=%d"
                              % (expected[:4], expected[-4:], buf[:4], buf[-4:], i))
        gt.wait()

    def test_seek_on_buffered_pipe (self):
        f = GreenFile(self.tempdir + "/TestFile", 'w+', 1024)
        self.assertEquals(f.tell(), 0)
        f.seek(0, 2)
        self.assertEquals(f.tell(), 0)
        f.write('1234567890')
        f.seek(0, 2)
        self.assertEquals(f.tell(), 10)
        f.seek(0)
        value = f.read(1)
        self.assertEqual(value, '1')
        self.assertEquals(f.tell(), 1)
        value = f.read(1)
        self.assertEqual(value, '2')
        self.assertEquals(f.tell(), 2)
        f.seek(0, 1)
        self.assertEqual(f.readline(), '34567890')
        f.seek(0)
        self.assertEqual(f.readline(), '1234567890')
        f.seek(0, 2)
        self.assertEqual(f.readline(), '')

    def test_truncate (self):
        f = GreenFile(self.tempdir + "/TestFile", 'w+', 1024)
        f.write('1234567890')
        f.truncate(9)
        self.assertEquals(f.tell(), 9)



if __name__ == '__main__':
    main()
