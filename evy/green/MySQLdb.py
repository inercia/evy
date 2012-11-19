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


__MySQLdb = __import__('MySQLdb')

__all__ = __MySQLdb.__all__
__patched__ = ["connect", "Connect", 'Connection', 'connections']

from evy.patcher import slurp_properties

slurp_properties(__MySQLdb, globals(),
                 ignore = __patched__, srckeys = dir(__MySQLdb))

from evy import tpool

__orig_connections = __import__('MySQLdb.connections').connections

def Connection (*args, **kw):
    conn = tpool.execute(__orig_connections.Connection, *args, **kw)
    return tpool.Proxy(conn, autowrap_names = ('cursor',))

connect = Connect = Connection

# replicate the MySQLdb.connections module but with a tpooled Connection factory
class MySQLdbConnectionsModule(object):
    pass

connections = MySQLdbConnectionsModule()
for var in dir(__orig_connections):
    if not var.startswith('__'):
        setattr(connections, var, getattr(__orig_connections, var))
connections.Connection = Connection

cursors = __import__('MySQLdb.cursors').cursors
converters = __import__('MySQLdb.converters').converters

# TODO support instantiating cursors.FooCursor objects directly
# TODO though this is a low priority, it would be nice if we supported
# subclassing evy.green.MySQLdb.connections.Connection
