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


__socket = __import__('socket')

__all__ = __socket.__all__
__patched__ = ['fromfd', 'socketpair', 'ssl', 'socket']

from evy.patcher import slurp_properties

slurp_properties(__socket, globals(),
                 ignore = __patched__, srckeys = dir(__socket))

os = __import__('os')
import sys
import warnings
from evy.hubs import get_hub
from evy.io.sockets import GreenSocket as socket
from evy.io.ssl import SSL as _SSL  # for exceptions
from evy.io.sockets import _GLOBAL_DEFAULT_TIMEOUT
from evy.io.pipes import _fileobject

try:
    __original_fromfd__ = __socket.fromfd

    def fromfd (*args):
        return socket(__original_fromfd__(*args))
except AttributeError:
    pass

try:
    __original_socketpair__ = __socket.socketpair

    def socketpair (*args):
        one, two = __original_socketpair__(*args)
        return socket(one), socket(two)
except AttributeError:
    pass


def _convert_to_sslerror (ex):
    """ Transliterates SSL.SysCallErrors to socket.sslerrors"""
    return sslerror((ex.args[0], ex.args[1]))


class GreenSSLObject(object):
    """
    Wrapper object around the SSLObjects returned by socket.ssl, which have a
    slightly different interface from SSL.Connection objects.
    """

    def __init__ (self, green_ssl_obj):
        """
        Should only be called by a 'green' socket.ssl
        """
        self.connection = green_ssl_obj
        try:
            # if it's already connected, do the handshake
            self.connection.getpeername()
        except:
            pass
        else:
            try:
                self.connection.do_handshake()
            except _SSL.SysCallError, e:
                raise _convert_to_sslerror(e)

    def read (self, n = 1024):
        """If n is provided, read n bytes from the SSL connection, otherwise read
        until EOF. The return value is a string of the bytes read."""
        try:
            return self.connection.read(n)
        except _SSL.ZeroReturnError:
            return ''
        except _SSL.SysCallError, e:
            raise _convert_to_sslerror(e)

    def write (self, s):
        """Writes the string s to the on the object's SSL connection.
        The return value is the number of bytes written. """
        try:
            return self.connection.write(s)
        except _SSL.SysCallError, e:
            raise _convert_to_sslerror(e)

    def server (self):
        """ Returns a string describing the server's certificate. Useful for debugging
        purposes; do not parse the content of this string because its format can't be
        parsed unambiguously. """
        return str(self.connection.get_peer_certificate().get_subject())

    def issuer (self):
        """Returns a string describing the issuer of the server's certificate. Useful
        for debugging purposes; do not parse the content of this string because its
        format can't be parsed unambiguously."""
        return str(self.connection.get_peer_certificate().get_issuer())


try:
    try:
        # >= Python 2.6
        from evy.patched import ssl as ssl_module

        sslerror = __socket.sslerror
        __socket.ssl

        def ssl (sock, certificate = None, private_key = None):
            warnings.warn("socket.ssl() is deprecated.  Use ssl.wrap_socket() instead.",
                          DeprecationWarning, stacklevel = 2)
            return ssl_module.sslwrap_simple(sock, private_key, certificate)
    except ImportError:
        # <= Python 2.5 compatibility
        sslerror = __socket.sslerror
        __socket.ssl

        def ssl (sock, certificate = None, private_key = None):
            from evy import util

            wrapped = util.wrap_ssl(sock, certificate, private_key)
            return GreenSSLObject(wrapped)
except AttributeError:
    # if the real socket module doesn't have the ssl method or sslerror
    # exception, we can't emulate them
    pass
