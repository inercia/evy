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


import os

from tests import patcher_test, skip_unless
from tests import get_database_auth
from tests.db_pool_test import postgres_requirement

psycopg_test_file = """
import os
import sys
import evy
evy.monkey_patch()
from evy import patcher
if not patcher.is_monkey_patched('psycopg'):
    print "Psycopg not monkeypatched"
    sys.exit(0)

count = [0]
def tick(totalseconds, persecond):
    for i in xrange(totalseconds*persecond):
        count[0] += 1
        evy.sleep(1.0/persecond)
        
dsn = os.environ['PSYCOPG_TEST_DSN']
import psycopg2    
def fetch(num, secs):
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    for i in range(num):
        cur.execute("select pg_sleep(%s)", (secs,))

f = evy.spawn(fetch, 2, 1)
t = evy.spawn(tick, 2, 100)
f.wait()
assert count[0] > 100, count[0]
print "done"
"""

class TestPatchingPsycopg(patcher_test.ProcessBase):

    @skip_unless(postgres_requirement)
    def test_psycopg_patched (self):
        if 'PSYCOPG_TEST_DSN' not in os.environ:
            # construct a non-json dsn for the subprocess
            psycopg_auth = get_database_auth()['psycopg2']
            if isinstance(psycopg_auth, str):
                dsn = psycopg_auth
            else:
                dsn = " ".join(["%s=%s" % (k, v) for k, v, in psycopg_auth.iteritems()])
            os.environ['PSYCOPG_TEST_DSN'] = dsn
        self.write_to_tempfile("psycopg_patcher", psycopg_test_file)
        output, lines = self.launch_subprocess('psycopg_patcher.py')
        if lines[0].startswith('Psycopg not monkeypatched'):
            print "Can't test psycopg2 patching; it's not installed."
            return
            # if there's anything wrong with the test program it'll have a stack trace
        self.assert_(lines[0].startswith('done'), output)

