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


from evy import patcher
from evy.patched import socket
from evy.patched import time
from evy.patched import httplib
from evy.patched import ftplib

to_patch = [('socket', socket), ('httplib', httplib),
    ('time', time), ('ftplib', ftplib)]
try:
    from evy.patched import ssl

    to_patch.append(('ssl', ssl))
except ImportError:
    pass

patcher.inject('urllib', globals(), *to_patch)

# patch a bunch of things that have imports inside the 
# function body; this is lame and hacky but I don't feel 
# too bad because urllib is a hacky pile of junk that no
# one should be using anyhow
URLopener.open_http = patcher.patch_function(URLopener.open_http, ('httplib', httplib))
if hasattr(URLopener, 'open_https'):
    URLopener.open_https = patcher.patch_function(URLopener.open_https, ('httplib', httplib))

URLopener.open_ftp = patcher.patch_function(URLopener.open_ftp, ('ftplib', ftplib))
ftpwrapper.init = patcher.patch_function(ftpwrapper.init, ('ftplib', ftplib))
ftpwrapper.retrfile = patcher.patch_function(ftpwrapper.retrfile, ('ftplib', ftplib))

del patcher

# Run test program when run as a script
if __name__ == '__main__':
    main()
