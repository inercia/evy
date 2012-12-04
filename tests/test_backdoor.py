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


import evy

from evy import backdoor
from evy.patched import socket
from evy.greenthread import sleep

from tests import LimitedTestCase, main

class BackdoorTest(LimitedTestCase):
    def test_server (self):
        listener = socket.socket()
        listener.bind(('localhost', 0))
        listener.listen(50)
        serv = evy.spawn(backdoor.backdoor_server, listener)
        client = socket.socket()
        client.connect(('localhost', listener.getsockname()[1]))
        f = client.makefile('rw')
        self.assert_('Python' in f.readline())
        f.readline()  # build info
        f.readline()  # help info
        self.assert_('InteractiveConsole' in f.readline())
        self.assertEquals('>>> ', f.read(4))
        f.write('print("hi")\n')
        f.flush()
        self.assertEquals('hi\n', f.readline())
        self.assertEquals('>>> ', f.read(4))
        f.close()
        client.close()
        serv.kill()
        # wait for the console to discover that it's dead
        sleep(0.1)


if __name__ == '__main__':
    main()
