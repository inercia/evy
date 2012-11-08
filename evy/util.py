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


import socket



__original_socket__ = socket.socket

try:
    # if ssl is available, use evy.green.ssl for our ssl implementation
    from evy.green import ssl

    def wrap_ssl (sock, certificate = None, private_key = None, server_side = False):
        return ssl.wrap_socket(sock,
                               keyfile = private_key, certfile = certificate,
                               server_side = server_side, cert_reqs = ssl.CERT_NONE,
                               ssl_version = ssl.PROTOCOL_SSLv23, ca_certs = None,
                               do_handshake_on_connect = True,
                               suppress_ragged_eofs = True)
except ImportError:
    # if ssl is not available, use PyOpenSSL
    def wrap_ssl (sock, certificate = None, private_key = None, server_side = False):
        try:
            from evy.green.OpenSSL import SSL
        except ImportError:
            raise ImportError("To use SSL with Eventlet, "
                              "you must install PyOpenSSL or use Python 2.6 or later.")
        context = SSL.Context(SSL.SSLv23_METHOD)
        if certificate is not None:
            context.use_certificate_file(certificate)
        if private_key is not None:
            context.use_privatekey_file(private_key)
        context.set_verify(SSL.VERIFY_NONE, lambda *x: True)

        connection = SSL.Connection(context, sock)
        if server_side:
            connection.set_accept_state()
        else:
            connection.set_connect_state()
        return connection


