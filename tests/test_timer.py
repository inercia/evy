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


from unittest import TestCase, main

import evy
from evy import hubs
from evy.hubs import timer

class TestTimer(TestCase):
    def test_copy (self):
        t = timer.Timer(0, lambda: None)
        t2 = t.copy()
        assert t.seconds == t2.seconds
        assert t.tpl == t2.tpl
        assert t.called == t2.called

    def test_schedule (self):
        hub = hubs.get_hub()
        # clean up the runloop, preventing side effects from previous tests
        # on this thread
        if hub.running:
            hub.abort()
            evy.sleep(0)
        called = []
        #t = timer.Timer(0, lambda: (called.append(True), hub.abort()))
        #t.schedule()
        # let's have a timer somewhere in the future; make sure abort() still works
        # (for pyevent, its dispatcher() does not exit if there is something scheduled)
        # XXX pyevent handles this, other hubs do not
        #hubs.get_hub().schedule_call_global(10000, lambda: (called.append(True), hub.abort()))
        hubs.get_hub().schedule_call_global(0, lambda: (called.append(True), hub.abort()))
        hub.default_sleep = lambda: 0.0
        hub.switch()
        assert called
        assert not hub.running


if __name__ == '__main__':
    main()
