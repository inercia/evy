import socket
import warnings



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


