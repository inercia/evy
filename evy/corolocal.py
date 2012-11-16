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


import weakref

from evy import greenthread

__all__ = ['get_ident', 'local']

def get_ident ():
    """ Returns ``id()`` of current greenlet.  Useful for debugging."""
    return id(greenthread.getcurrent())


class _localbase(object):
    """
    This class is used to store off the constructor arguments in a local variable without
    calling __init__ directly
    """

    __slots__ = '_local__args', '_local__greens'

    def __new__ (cls, *args, **kw):
        self = object.__new__(cls)
        object.__setattr__(self, '_local__args', (args, kw))
        object.__setattr__(self, '_local__greens', weakref.WeakKeyDictionary())
        if (args or kw) and (cls.__init__ is object.__init__):
            raise TypeError("Initialization arguments are not supported")
        return self


def _patch (thrl):
    greens = object.__getattribute__(thrl, '_local__greens')

    # until we can store the localdict on greenlets themselves,
    # we store it in _local__greens on the local object
    cur = greenthread.getcurrent()
    if cur not in greens:
        # must be the first time we've seen this greenlet, call __init__
        greens[cur] = {}
        cls = type(thrl)
        if cls.__init__ is not object.__init__:
            args, kw = object.__getattribute__(thrl, '_local__args')
            thrl.__init__(*args, **kw)
    object.__setattr__(thrl, '__dict__', greens[cur])



class local(_localbase):
    def __getattribute__ (self, attr):
        _patch(self)
        return object.__getattribute__(self, attr)

    def __setattr__ (self, attr, value):
        _patch(self)
        return object.__setattr__(self, attr, value)

    def __delattr__ (self, attr):
        _patch(self)
        return object.__delattr__(self, attr)
