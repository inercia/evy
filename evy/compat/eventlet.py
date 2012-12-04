#
# Evy - a concurrent networking library for Python
#
# Unless otherwise noted, the files in Evy are under the following MIT license:
#
# Copyright (c) 2012, Alvaro Saurin
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




try:
    from evy import version_info, __version__

    from evy.green import threads as greenthread
    from evy import greenpool
    from evy import queue
    from evy import timeout
    from evy import patcher
    from evy import convenience
    import greenlet

    sleep = greenthread.sleep
    spawn = greenthread.spawn
    spawn_n = greenthread.spawn_n
    spawn_after = greenthread.spawn_after
    kill = greenthread.kill

    Timeout = TimeoutError = timeout.Timeout
    with_timeout = timeout.with_timeout

    GreenPool = greenpool.GreenPool
    GreenPile = greenpool.GreenPile

    Queue = queue.Queue

    import_patched = patcher.import_patched
    monkey_patch = patcher.monkey_patch

    connect = convenience.connect
    listen = convenience.listen
    serve = convenience.serve
    StopServe = convenience.StopServe
    wrap_ssl = convenience.wrap_ssl

    getcurrent = greenlet.greenlet.getcurrent

except ImportError, e:
    # This is to make Debian packaging easier, it ignores import
    # errors of greenlet so that the packager can still at least
    # access the version.  Also this makes easy_install a little quieter
    if 'greenlet' not in str(e):
        # any other exception should be printed
        import traceback

        traceback.print_exc()
