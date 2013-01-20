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


__select = __import__('select')
error = __select.error


from evy.green.threads import getcurrent
from evy.hubs import get_hub

__patched__ = ['select']


def get_fileno (obj):
    # The purpose of this function is to exactly replicate
    # the behavior of the select module when confronted with
    # abnormal filenos; the details are extensively tested in
    # the stdlib test/test_select.py.
    try:
        f = obj.fileno
    except AttributeError:
        if not isinstance(obj, (int, long)):
            raise TypeError("Expected int or long, got " + type(obj))
        return obj
    else:
        rv = f()
        if not isinstance(rv, (int, long)):
            raise TypeError("Expected int or long, got " + type(rv))
        return rv


def select (read_list, write_list, error_list, timeout = None):
    # error checking like this is required by the stdlib unit tests
    if timeout is not None:
        try:
            timeout = float(timeout)
        except ValueError:
            raise TypeError("Expected number for timeout")
    hub = get_hub()
    t = None
    current = getcurrent()
    assert hub.greenlet is not current, 'do not call blocking functions from the mainloop'
    ds = {}

    for r in read_list:
        ds[get_fileno(r)] = {'read': r}

    for w in write_list:
        ds.setdefault(get_fileno(w), {})['write'] = w

    for e in error_list:
        ds.setdefault(get_fileno(e), {})['error'] = e

    listeners = []

    def on_read (d):
        original = ds[get_fileno(d)]['read']
        current.switch(([original], [], []))

    def on_write (d):
        original = ds[get_fileno(d)]['write']
        current.switch(([], [original], []))

    def on_error (d, _err = None):
        original = ds[get_fileno(d)]['error']
        current.switch(([], [], [original]))

    def on_timeout ():
        current.switch(([], [], []))

    if timeout is not None:
        t = hub.schedule_call_global(timeout, on_timeout)
    try:
        for k, v in ds.iteritems():
            if v.get('read'):
                listeners.append(hub.add(hub.READ, k, on_read))
            if v.get('write'):
                listeners.append(hub.add(hub.WRITE, k, on_write))
        try:
            return hub.switch()
        finally:
            for l in listeners:
                hub.remove(l)
    finally:
        if t is not None:
            t.cancel()

