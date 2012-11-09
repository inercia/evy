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
This script simply gets the paths correct for testing evy with the
hub extension for Nose.
"""

import nose
from os.path import dirname, realpath, abspath
import sys

parent_dir = dirname(dirname(realpath(abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# hacky hacks: skip test__api_timeout when under 2.4 because otherwise it SyntaxErrors
if sys.version_info < (2, 5):
    argv = sys.argv + ["--exclude=.*_with_statement.*"]
else:
    argv = sys.argv

# hudson does a better job printing the test results if the exit value is 0
zero_status = '--force-zero-status'
if zero_status in argv:
    argv.remove(zero_status)
    launch = nose.run
else:
    launch = nose.main

launch(argv = argv)
