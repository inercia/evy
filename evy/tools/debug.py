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



"""
The debug module contains utilities and functions for better
debugging Evy-powered applications.
"""

import os
import sys
import linecache
import re
import inspect

__all__ = ['spew', 'unspew', 'format_hub_listeners', 'format_hub_timers',
           'hub_listener_stacks', 'hub_exceptions', 'tpool_exceptions',
           'hub_timer_stacks',
           'hub_blocking_detection']

_token_splitter = re.compile('\W+')

class Spew(object):
    """
    """

    def __init__ (self, trace_names = None, show_values = True):
        self.trace_names = trace_names
        self.show_values = show_values

    def __call__ (self, frame, event, arg):
        if event == 'line':
            lineno = frame.f_lineno
            if '__file__' in frame.f_globals:
                filename = frame.f_globals['__file__']
                if (filename.endswith('.pyc') or
                    filename.endswith('.pyo')):
                    filename = filename[:-1]
                name = frame.f_globals['__name__']
                line = linecache.getline(filename, lineno)
            else:
                name = '[unknown]'
                try:
                    src = inspect.getsourcelines(frame)
                    line = src[lineno]
                except IOError:
                    line = 'Unknown code named [%s].  VM instruction #%d' % (
                        frame.f_code.co_name, frame.f_lasti)
            if self.trace_names is None or name in self.trace_names:
                print '%s:%s: %s' % (name, lineno, line.rstrip())
                if not self.show_values:
                    return self
                details = []
                tokens = _token_splitter.split(line)
                for tok in tokens:
                    if tok in frame.f_globals:
                        details.append('%s=%r' % (tok, frame.f_globals[tok]))
                    if tok in frame.f_locals:
                        details.append('%s=%r' % (tok, frame.f_locals[tok]))
                if details:
                    print "\t%s" % ' '.join(details)
        return self


def spew (trace_names = None, show_values = False):
    """Install a trace hook which writes incredibly detailed logs
    about what code is being executed to stdout.
    """
    sys.settrace(Spew(trace_names, show_values))


def unspew ():
    """Remove the trace hook installed by spew.
    """
    sys.settrace(None)


def format_hub_listeners ():
    """ Returns a formatted string of the current listeners on the current
    hub.  This can be useful in determining what's going on in the event system,
    especially when used in conjunction with :func:`hub_listener_stacks`.
    """
    from evy import hubs

    hub = hubs.get_hub()
    result = ['READERS:']
    for l in hub.get_readers():
        result.append(repr(l))
    result.append('WRITERS:')
    for l in hub.get_writers():
        result.append(repr(l))
    return os.linesep.join(result)


def format_hub_timers ():
    """ Returns a formatted string of the current timers on the current
    hub.  This can be useful in determining what's going on in the event system,
    especially when used in conjunction with :func:`hub_timer_stacks`.
    """
    from evy import hubs

    hub = hubs.get_hub()
    result = ['TIMERS:']
    for l in hub.timers:
        result.append(repr(l))
    return os.linesep.join(result)


def hub_listener_stacks (state = False):
    """Toggles whether or not the hub records the stack when clients register 
    listeners on file descriptors.  This can be useful when trying to figure 
    out what the hub is up to at any given moment.  To inspect the stacks
    of the current listeners, call :func:`format_hub_listeners` at critical
    junctures in the application logic.
    """
    from evy import hubs

    hubs.get_hub().set_debug_listeners(state)


def hub_timer_stacks (state = False):
    """Toggles whether or not the hub records the stack when timers are set.  
    To inspect the stacks of the current timers, call :func:`format_hub_timers` 
    at critical junctures in the application logic.
    """
    from evy.hubs import timer

    timer._g_debug = state

def hub_exceptions (state = True):
    """Toggles whether the hub prints exceptions that are raised from its
    timers.  This can be useful to see how greenthreads are terminating.
    """
    from evy import hubs

    hubs.get_hub().set_timer_exceptions(state)
    from evy.green import pools as greenpool

    greenpool.DEBUG = state


def tpool_exceptions (state = False):
    """Toggles whether tpool itself prints exceptions that are raised from 
    functions that are executed in it, in addition to raising them like
    it normally does."""
    from evy import tpool

    tpool.QUIET = not state


def hub_blocking_detection (state = False, resolution = 1):
    """
    Toggles whether Evy makes an effort to detect blocking
    behavior in an application.

    It does this by telling the kernel to raise a SIGALARM after a
    short timeout, and clearing the timeout every time the hub
    greenlet is resumed.  Therefore, any code that runs for a long
    time without yielding to the hub will get interrupted by the
    blocking detector (don't use it in production!).

    The *resolution* argument governs how long the SIGALARM timeout
    waits in seconds.  If on Python 2.6 or later, the implementation
    uses :func:`signal.setitimer` and can be specified as a
    floating-point value.  On 2.5 or earlier, 1 second is the minimum.
    The shorter the resolution, the greater the chance of false
    positives.
    """
    from evy import hubs

    assert resolution > 0
    hubs.get_hub().debug_blocking = state
    hubs.get_hub().debug_blocking_resolution = resolution
    if not state:
        hubs.get_hub().block_detect_post()
    
