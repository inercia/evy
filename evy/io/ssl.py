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
#


# import SSL module here so we can refer to evy.io.ssl.SSL.exceptionclass
try:
    from OpenSSL import SSL
except ImportError:
    # pyOpenSSL not installed, define exceptions anyway for convenience
    class SSL(object):
        class WantWriteError(object):
            pass

        class WantReadError(object):
            pass

        class ZeroReturnError(object):
            pass

        class SysCallError(object):
            pass



def wrap_ssl (sock, *a, **kw):
    """
    Convenience function for converting a regular socket into an
    SSL socket.  Has the same interface as :func:`ssl.wrap_socket`,
    but works on 2.5 or earlier, using PyOpenSSL (though note that it
    ignores the *cert_reqs*, *ssl_version*, *ca_certs*,
    *do_handshake_on_connect*, and *suppress_ragged_eofs* arguments
    when using PyOpenSSL).

    The preferred idiom is to call wrap_ssl directly on the creation
    method, e.g., ``wrap_ssl(connect(addr))`` or
    ``wrap_ssl(listen(addr), server_side=True)``. This way there is
    no "naked" socket sitting around to accidentally corrupt the SSL
    session.

    :return Green SSL object.
    """
    return wrap_ssl_impl(sock, *a, **kw)

try:
    from evy.patched import ssl
    wrap_ssl_impl = ssl.wrap_socket
except ImportError:
    # < 2.6, trying PyOpenSSL
    try:
        from evy.patched.OpenSSL import SSL

        def wrap_ssl_impl (sock, keyfile = None, certfile = None, server_side = False,
                           cert_reqs = None, ssl_version = None, ca_certs = None,
                           do_handshake_on_connect = True,
                           suppress_ragged_eofs = True, ciphers = None):
            # theoretically the ssl_version could be respected in this
            # next line
            context = SSL.Context(SSL.SSLv23_METHOD)
            if certfile is not None:
                context.use_certificate_file(certfile)
            if keyfile is not None:
                context.use_privatekey_file(keyfile)
            context.set_verify(SSL.VERIFY_NONE, lambda *x: True)

            connection = SSL.Connection(context, sock)
            if server_side:
                connection.set_accept_state()
            else:
                connection.set_connect_state()
            return connection
    except ImportError:
        def wrap_ssl_impl (*a, **kw):
            raise ImportError("To use SSL with Eventlet, "
                              "you must install PyOpenSSL or use Python 2.6 or later.")

