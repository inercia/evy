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


from tests.test_patcher import ProcessBase


class ForkTest(ProcessBase):

    def test_simple (self):
        newmod = '''
import evy
import os
import sys
import signal

from evy import sleep
from evy.timeout import Timeout

mydir = %r
signal_file = os.path.join(mydir, "output.txt")
pid = os.fork()
if (pid != 0):
  Timeout(10)
  try:
    port = None
    while True:
      try:
        contents = open(signal_file, "rb").read()
        port = int(contents.split()[0])
        break
      except (IOError, IndexError, ValueError, TypeError):
        sleep(0.1)
    connect(('127.0.0.1', port))
    while True:
      try:
        contents = open(signal_file, "rb").read()
        result = contents.split()[1]
        break
      except (IOError, IndexError):
        sleep(0.1)
    print 'result', result
  finally:
    os.kill(pid, signal.SIGTERM)
else:
  try:
    s = listen(('', 0))
    fd = open(signal_file, "wb")
    fd.write(str(s.getsockname()[1]))
    fd.write("\\n")
    fd.flush()
    s.accept()
    fd.write("done")
    fd.flush()
  finally:
    fd.close()
'''
        self.write_to_tempfile("newmod", newmod % self.tempdir)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(lines[0], "result done", output)
