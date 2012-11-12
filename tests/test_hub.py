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


from __future__ import with_statement

from tests import LimitedTestCase, main, skip_with_pyevent, skip_if_no_itimer
import time
import evy
from evy import hubs
from evy.green import socket

DELAY = 0.001

def noop ():
    pass


class TestTimerCleanup(LimitedTestCase):
    TEST_TIMEOUT = 2

    @skip_with_pyevent
    def test_cancel_immediate (self):
        hub = hubs.get_hub()
        stimers = hub.get_timers_count()
        scanceled = hub.timers_canceled
        for i in xrange(2000):
            t = hubs.get_hub().schedule_call_global(60, noop)
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
            # there should be fewer than 1000 new timers and canceled
        self.assert_less_than_equal(hub.get_timers_count(), 1000 + stimers)
        self.assert_less_than_equal(hub.timers_canceled, 1000)


    @skip_with_pyevent
    def test_cancel_accumulated (self):
        hub = hubs.get_hub()
        stimers = hub.get_timers_count()
        scanceled = hub.timers_canceled
        for i in xrange(2000):
            t = hubs.get_hub().schedule_call_global(60, noop)
            evy.sleep()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1, hub.timers)
            # there should be fewer than 1000 new timers and canceled
        self.assert_less_than_equal(hub.get_timers_count(), 1000 + stimers)
        self.assert_less_than_equal(hub.timers_canceled, 1000)

    @skip_with_pyevent
    def test_cancel_proportion (self):
        # if fewer than half the pending timers are canceled, it should
        # not clean them out
        hub = hubs.get_hub()
        uncanceled_timers = []
        stimers = hub.get_timers_count()
        scanceled = hub.timers_canceled
        for i in xrange(1000):
            # 2/3rds of new timers are uncanceled
            t = hubs.get_hub().schedule_call_global(60, noop)
            t2 = hubs.get_hub().schedule_call_global(60, noop)
            t3 = hubs.get_hub().schedule_call_global(60, noop)
            evy.sleep()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count() + 1)
            uncanceled_timers.append(t2)
            uncanceled_timers.append(t3)
            # 3000 new timers, plus a few extras
        self.assert_less_than_equal(stimers + 3000,
                                    stimers + hub.get_timers_count())
        self.assertEqual(hub.timers_canceled, 1000)
        for t in uncanceled_timers:
            t.cancel()
            self.assert_less_than_equal(hub.timers_canceled,
                                        hub.get_timers_count())
        evy.sleep()


class TestScheduleCall(LimitedTestCase):
    def test_local (self):
        lst = [1]
        evy.spawn(hubs.get_hub().schedule_call_local, DELAY, lst.pop)
        evy.sleep(0)
        evy.sleep(DELAY * 2)
        assert lst == [1], lst

    def test_global (self):
        lst = [1]
        evy.spawn(hubs.get_hub().schedule_call_global, DELAY, lst.pop)
        evy.sleep(0)
        evy.sleep(DELAY * 2)
        assert lst == [], lst

    def test_ordering (self):
        lst = []
        hubs.get_hub().schedule_call_global(DELAY * 2, lst.append, 3)
        hubs.get_hub().schedule_call_global(DELAY, lst.append, 1)
        hubs.get_hub().schedule_call_global(DELAY, lst.append, 2)
        while len(lst) < 3:
            evy.sleep(DELAY)
        self.assertEquals(lst, [1, 2, 3])


class TestDebug(LimitedTestCase):
    def test_debug_listeners (self):
        hubs.get_hub().set_debug_listeners(True)
        hubs.get_hub().set_debug_listeners(False)

    def test_timer_exceptions (self):
        hubs.get_hub().set_timer_exceptions(True)
        hubs.get_hub().set_timer_exceptions(False)


class TestExceptionInMainloop(LimitedTestCase):
    def test_sleep (self):
        # even if there was an error in the mainloop, the hub should continue to work
        start = time.time()
        evy.sleep(DELAY)
        delay = time.time() - start

        assert delay >= DELAY * 0.9, 'sleep returned after %s seconds (was scheduled for %s)' % (
        delay, DELAY)

        def fail ():
            1 // 0

        hubs.get_hub().schedule_call_global(0, fail)

        start = time.time()
        evy.sleep(DELAY)
        delay = time.time() - start

        assert delay >= DELAY * 0.9, 'sleep returned after %s seconds (was scheduled for %s)' % (
        delay, DELAY)


class TestHubSelection(LimitedTestCase):
    def test_explicit_hub (self):
        if getattr(hubs.get_hub(), 'uses_twisted_reactor', None):
            # doesn't work with twisted
            return
        oldhub = hubs.get_hub()
        try:
            hubs.use_hub(Foo)
            self.assert_(isinstance(hubs.get_hub(), Foo), hubs.get_hub())
        finally:
            hubs._threadlocal.hub = oldhub


class TestHubBlockingDetector(LimitedTestCase):
    TEST_TIMEOUT = 10

    @skip_with_pyevent
    def test_block_detect (self):
        def look_im_blocking ():
            import time

            time.sleep(2)

        from evy import debug

        debug.hub_blocking_detection(True)
        gt = evy.spawn(look_im_blocking)
        self.assertRaises(RuntimeError, gt.wait)
        debug.hub_blocking_detection(False)

    @skip_with_pyevent
    @skip_if_no_itimer
    def test_block_detect_with_itimer (self):
        def look_im_blocking ():
            import time

            time.sleep(0.5)

        from evy import debug

        debug.hub_blocking_detection(True, resolution = 0.1)
        gt = evy.spawn(look_im_blocking)
        self.assertRaises(RuntimeError, gt.wait)
        debug.hub_blocking_detection(False)


class TestSuspend(LimitedTestCase):
    TEST_TIMEOUT = 3

    def test_suspend_doesnt_crash (self):
        import errno
        import os
        import shutil
        import signal
        import subprocess
        import sys
        import tempfile

        self.tempdir = tempfile.mkdtemp('test_suspend')
        filename = os.path.join(self.tempdir, 'test_suspend.py')
        fd = open(filename, "w")
        fd.write("""import evy
evy.Timeout(0.5)
try:
   evy.listen(("127.0.0.1", 0)).accept()
except evy.Timeout:
   print "exited correctly"
""")
        fd.close()
        python_path = os.pathsep.join(sys.path + [self.tempdir])
        new_env = os.environ.copy()
        new_env['PYTHONPATH'] = python_path
        p = subprocess.Popen([sys.executable,
                              os.path.join(self.tempdir, filename)],
                                                                   stdout = subprocess.PIPE,
                                                                   stderr = subprocess.STDOUT,
                                                                   env = new_env)
        evy.sleep(0.4)  # wait for process to hit accept
        os.kill(p.pid, signal.SIGSTOP) # suspend and resume to generate EINTR
        os.kill(p.pid, signal.SIGCONT)
        output, _ = p.communicate()
        lines = [l for l in output.split("\n") if l]
        self.assert_("exited correctly" in lines[-1])
        shutil.rmtree(self.tempdir)


class TestBadFilenos(LimitedTestCase):
    @skip_with_pyevent
    def test_repeated_selects (self):
        from evy.green import select

        self.assertRaises(ValueError, select.select, [-1], [], [])
        self.assertRaises(ValueError, select.select, [-1], [], [])


from tests.test_patcher import ProcessBase

class TestFork(ProcessBase):
    @skip_with_pyevent
    def test_fork (self):
        new_mod = """
import os
import evy
server = evy.listen(('localhost', 12345))
t = evy.Timeout(0.01)
try:
    new_sock, address = server.accept()
except evy.Timeout, t:
    pass

pid = os.fork()
if not pid:
    t = evy.Timeout(0.1)
    try:
        new_sock, address = server.accept()
    except evy.Timeout, t:
        print "accept blocked"
        
else:
    kpid, status = os.wait()
    assert kpid == pid
    assert status == 0
    print "child died ok"
"""
        self.write_to_tempfile("newmod", new_mod)
        output, lines = self.launch_subprocess('newmod.py')
        self.assertEqual(len(lines), 3, output)
        self.assert_("accept blocked" in lines[0])
        self.assert_("child died ok" in lines[1])


class TestDeadRunLoop(LimitedTestCase):
    TEST_TIMEOUT = 2

    class CustomException(Exception):
        pass

    def test_kill (self):
        """ Checks that killing a process after the hub runloop dies does
        not immediately return to hub greenlet's parent and schedule a
        redundant timer. """
        hub = hubs.get_hub()

        def dummyproc ():
            hub.switch()

        g = evy.spawn(dummyproc)
        evy.sleep(0)  # let dummyproc run
        assert hub.greenlet.parent == evy.greenthread.getcurrent()
        self.assertRaises(KeyboardInterrupt, hub.greenlet.throw,
                          KeyboardInterrupt())

        # kill dummyproc, this schedules a timer to return execution to
        # this greenlet before throwing an exception in dummyproc.
        # it is from this timer that execution should be returned to this
        # greenlet, and not by propogating of the terminating greenlet.
        g.kill()
        with evy.Timeout(0.5, self.CustomException()):
            # we now switch to the hub, there should be no existing timers
            # that switch back to this greenlet and so this hub.switch()
            # call should block indefinately.
            self.assertRaises(self.CustomException, hub.switch)

    def test_parent (self):
        """ Checks that a terminating greenthread whose parent
        was a previous, now-defunct hub greenlet returns execution to
        the hub runloop and not the hub greenlet's parent. """
        hub = hubs.get_hub()

        def dummyproc ():
            pass

        g = evy.spawn(dummyproc)
        assert hub.greenlet.parent == evy.greenthread.getcurrent()
        self.assertRaises(KeyboardInterrupt, hub.greenlet.throw,
                          KeyboardInterrupt())

        assert not g.dead  # check dummyproc hasn't completed
        with evy.Timeout(0.5, self.CustomException()):
            # we now switch to the hub which will allow
            # completion of dummyproc.
            # this should return execution back to the runloop and not
            # this greenlet so that hub.switch() would block indefinately.
            self.assertRaises(self.CustomException, hub.switch)
        assert g.dead  # sanity check that dummyproc has completed


class Foo(object):
    pass

if __name__ == '__main__':
    main()

