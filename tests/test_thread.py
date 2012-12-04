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


import weakref

import evy

from evy import event
from evy import corolocal

from evy.patched import thread
from evy.green.threads import sleep, getcurrent

from tests import LimitedTestCase, skipped

class Locals(LimitedTestCase):
    def passthru (self, *args, **kw):
        self.results.append((args, kw))
        return args, kw

    def setUp (self):
        self.results = []
        super(Locals, self).setUp()

    def tearDown (self):
        self.results = []
        super(Locals, self).tearDown()

    @skipped  # cause it relies on internal details of corolocal that are no longer true
    def test_simple (self):
        tls = thread._local()
        g_ids = []
        evt = event.Event()

        def setter (tls, v):
            g_id = id(getcurrent())
            g_ids.append(g_id)
            tls.value = v
            evt.wait()

        thread.start_new_thread(setter, args = (tls, 1))
        thread.start_new_thread(setter, args = (tls, 2))
        sleep()
        objs = object.__getattribute__(tls, "__objs")
        self.failUnlessEqual(sorted(g_ids), sorted(objs.keys()))
        self.failUnlessEqual(objs[g_ids[0]]['value'], 1)
        self.failUnlessEqual(objs[g_ids[1]]['value'], 2)
        self.failUnlessRaises(AttributeError, lambda: tls.value)
        evt.send("done")
        sleep()

    def test_assignment (self):
        my_local = corolocal.local()
        my_local.a = 1

        def do_something ():
            my_local.b = 2
            self.assertEqual(my_local.b, 2)
            try:
                my_local.a
                self.fail()
            except AttributeError:
                pass

        evy.spawn(do_something).wait()
        self.assertEqual(my_local.a, 1)

    def test_calls_init (self):
        init_args = []

        class Init(corolocal.local):
            def __init__ (self, *args):
                init_args.append((args, evy.getcurrent()))

        my_local = Init(1, 2, 3)
        self.assertEqual(init_args[0][0], (1, 2, 3))
        self.assertEqual(init_args[0][1], evy.getcurrent())

        def do_something ():
            my_local.foo = 'bar'
            self.assertEqual(len(init_args), 2, init_args)
            self.assertEqual(init_args[1][0], (1, 2, 3))
            self.assertEqual(init_args[1][1], evy.getcurrent())

        evy.spawn(do_something).wait()

    def test_calling_methods (self):
        class Caller(corolocal.local):
            def callme (self):
                return self.foo

        my_local = Caller()
        my_local.foo = "foo1"
        self.assertEquals("foo1", my_local.callme())

        def do_something ():
            my_local.foo = "foo2"
            self.assertEquals("foo2", my_local.callme())

        evy.spawn(do_something).wait()

        my_local.foo = "foo3"
        self.assertEquals("foo3", my_local.callme())

    def test_no_leaking (self):
        refs = weakref.WeakKeyDictionary()
        my_local = corolocal.local()

        class X(object):
            pass

        def do_something (i):
            o = X()
            refs[o] = True
            my_local.foo = o

        p = evy.GreenPool()
        for i in xrange(100):
            p.spawn(do_something, i)
        p.waitall()
        del p
        # at this point all our coros have terminated
        self.assertEqual(len(refs), 1)
