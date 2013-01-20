#!/usr/bin/env python
# Portions of this code taken from the gogreen project:
#   http://github.com/slideinc/gogreen
#
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""
Non-blocking DNS support for Evy
"""



import sys

import pyuv
import pycares

from evy.hubs import get_hub
from evy.event import Event
from evy.timeout import Timeout

import socket
from _socket import getservbyname, gaierror, error


DNS_QUERY_TIMEOUT = 10.0


ARES_ERR_MAP = {
    'ARES_EAGAIN' :    socket.EAI_AGAIN,
    'ARES_EFAIL' :     socket.EAI_FAIL,
    'ARES_ENONAME' :   socket.EAI_NONAME,
    'ARES_ENODATA' :   socket.EAI_NODATA
}

def is_ipv4_addr (host):
    """
    Return true if host is a valid IPv4 address in dotted quad notation.
    """
    try:
        d1, d2, d3, d4 = map(int, host.split('.'))
    except (ValueError, AttributeError):
        return False

    if 0 <= d1 <= 255 and 0 <= d2 <= 255 and 0 <= d3 <= 255 and 0 <= d4 <= 255:
        return True
    return False


#
# Resolver instance used to perfrom DNS lookups.
#
class FakeAnswer(list):
    expiration = 0


class FakeRecord(object):
    pass


class CaresResolver(object):
    """
    The C-ares DNS resolver
    """

    def __init__(self, loop):
        self._channel = pycares.Channel(sock_state_cb=self._sock_state_cb)
        self.loop = loop
        self._timer = pyuv.Timer(self.loop)
        self._fd_map = {}

    def _sock_state_cb(self, fd, readable, writable):
        if readable or writable:
            if fd not in self._fd_map:
                # New socket
                handle = pyuv.Poll(self.loop, fd)
                handle.fd = fd
                self._fd_map[fd] = handle
            else:
                handle = self._fd_map[fd]
            if not self._timer.active:
                self._timer.start(self._timer_cb, 1.0, 1.0)
            handle.start(pyuv.UV_READABLE if readable else 0 | pyuv.UV_WRITABLE if writable else 0, self._poll_cb)
        else:
            # Socket is now closed
            handle = self._fd_map.pop(fd)
            handle.close()
            if not self._fd_map:
                self._timer.stop()

    def _timer_cb(self, timer):
        self._channel.process_fd(pycares.ARES_SOCKET_BAD, pycares.ARES_SOCKET_BAD)

    def _poll_cb(self, handle, events, error):
        read_fd = handle.fd
        write_fd = handle.fd
        if error is not None:
            # There was an error, pretend the socket is ready
            self._channel.process_fd(read_fd, write_fd)
            return

        if not events & pyuv.UV_READABLE:
            read_fd = pycares.ARES_SOCKET_BAD

        if not events & pyuv.UV_WRITABLE:
            write_fd = pycares.ARES_SOCKET_BAD
        self._channel.process_fd(read_fd, write_fd)

    def _lookup_port(self, port, socktype):
        socktypes = []

        if isinstance(port, str):
            try:
                port = int(port)
            except ValueError:
                try:
                    if socktype == 0:
                        origport = port
                        try:
                            port = getservbyname(port, 'tcp')
                            socktypes.append(socket.SOCK_STREAM)
                        except error:
                            port = getservbyname(port, 'udp')
                            socktypes.append(socket.SOCK_DGRAM)
                        else:
                            try:
                                if port == getservbyname(origport, 'udp'):
                                    socktypes.append(socket.SOCK_DGRAM)
                            except error:
                                pass
                    elif socktype == socket.SOCK_STREAM:
                        port = getservbyname(port, 'tcp')
                    elif socktype == socket.SOCK_DGRAM:
                        port = getservbyname(port, 'udp')
                    else:
                        raise gaierror(socket.EAI_SERVICE, 'Servname not supported for ai_socktype')
                except error:
                    ex = sys.exc_info()[1]
                    if 'not found' in str(ex):
                        raise gaierror(socket.EAI_SERVICE, 'Servname not supported for ai_socktype')
                    else:
                        raise gaierror(str(ex))
                except UnicodeEncodeError:
                    raise error('Int or String expected')
        elif port is None:
            port = 0
        elif isinstance(port, int):
            pass
        else:
            raise error('Int or String expected')
        port = int(port % 65536)
        if not socktypes and socktype:
            socktypes.append(socktype)
        return port, socktypes

    def query(self, query_type, name, cb):
        self._channel.query(query_type, name, cb)

    def gethostbyname(self, name, cb):
        self._channel.gethostbyname(name, socket.AF_INET, cb)

    def getnameinfo(self, addr, flags, cb):
        self._channel.getnameinfo(addr, flags, cb)


#
# cache
#
_resolver_hub = get_hub()
resolver = CaresResolver(_resolver_hub.uv_loop)



def resolve (name):
    """
    Resolve the *name*, returning a list of IP addresses

    :param name: the name we want to resolve
    :return: a list of IP addresses
    """
    if is_ipv4_addr(name):
        return [name]

    rrset = []
    resolved = Event()

    def _resolv_callback(result, errorno):
        try:
            if errorno:
                e = pycares.errno.errorcode[errorno]
                msg = pycares.errno.strerror(errorno)
                resolved.send_exception(socket.gaierror(e, msg))
            else:
                resolved.send(result)
        except Exception, e:
            resolved.send_exception(e)

    try:
        with Timeout(DNS_QUERY_TIMEOUT):
            resolver.query(name, pycares.QUERY_TYPE_A, _resolv_callback)
            rrset = resolved.wait()

    except Timeout, e:
        raise socket.gaierror(socket.EAI_AGAIN, 'Lookup timed out')
    except Exception, e:
        raise socket.gaierror(socket.EAI_NODATA, 'No address associated with hostname "%s"' % name)

    if len(rrset) == 0:
        raise socket.gaierror(socket.EAI_NODATA, 'No address associated with hostname "%s"' % name)

    return rrset

#
# methods
#
def getaliases (host):
    """
    Checks for aliases of the given hostname (cname records)
    returns a list of alias targets
    will return an empty list if no aliases
    """
    aliases = None
    resolved = Event()

    def _resolv_callback(result, errorno):
        try:
            if errorno:
                e = pycares.errno.errorcode[errorno]
                msg = pycares.errno.strerror(errorno)
                resolved.send_exception(socket.gaierror(e, msg))
            else:
                resolved.send(result)
        except Exception, e:
            resolved.send_exception(e)

    try:
        with Timeout(DNS_QUERY_TIMEOUT):
            resolver.query(host, pycares.QUERY_TYPE_CNAME, _resolv_callback)
            aliases = resolved.wait()

    except Timeout, e:
        raise socket.gaierror(socket.EAI_AGAIN, 'Lookup timed out')
    except Exception, e:
        raise socket.gaierror(socket.EAI_NODATA, 'No address associated with hostname')

    return aliases

def getaddrinfo (host, port, family = 0, socktype = 0, proto = 0, flags = 0):
    """
    Replacement for Python's socket.getaddrinfo.
    """
    if not host:
        host = 'localhost'

    socktype = socktype or socket.SOCK_STREAM

    if is_ipv4_addr(host):
        return [(socket.AF_INET, socktype, proto, '', (host, port))]

    rrset = resolve(host)
    value = []

    for rr in rrset:
        value.append((socket.AF_INET, socktype, proto, '', (rr, port)))
    return value


def gethostbyname (hostname):
    """
    Replacement for Python's socket.gethostbyname.

    Currently only supports IPv4.
    """
    if is_ipv4_addr(hostname):
        return hostname

    ips = []
    resolved = Event()

    def _resolv_callback(result, errorno):
        try:
            if errorno:
                e = pycares.errno.errorcode[errorno]
                msg = pycares.errno.strerror(errorno)
                ee = ARES_ERR_MAP[e]
                resolved.send_exception(socket.gaierror(ee, msg))
            else:
                resolved.send(result)
        except Exception, e:
            resolved.send_exception(e)

    try:
        with Timeout(DNS_QUERY_TIMEOUT):
            resolver.query(hostname, pycares.QUERY_TYPE_CNAME, _resolv_callback)
            ips = resolved.wait()

    except Timeout, e:
        raise socket.gaierror(socket.EAI_AGAIN, 'Lookup timed out')
    except Exception, e:
        raise socket.gaierror(socket.EAI_NODATA, 'No address associated with hostname')

    if len(ips) == 0:
        raise socket.gaierror(socket.EAI_NODATA, 'No address associated with hostname')

    return ips[0]


def gethostbyname_ex (hostname):
    """
    Replacement for Python's socket.gethostbyname_ex.

    Currently only supports IPv4.
    """
    if is_ipv4_addr(hostname):
        return (hostname, [], [hostname])

    rrset = resolve(hostname)
    addrs = []

    for rr in rrset:
        addrs.append(rr)
    return (hostname, [], addrs)


def getnameinfo (addr, flags):
    """
    Replacement for Python's socket.getnameinfo.

    The flags can be:

    * NI_NAMEREQD If set, then an error is returned if the hostname cannot be determined.
    * NI_DGRAM: If set, then the service is datagram (UDP) based rather than stream (TCP) based. This is required for the few ports (512-514) that have different services for UDP and TCP.
    * NI_NOFQDN: If set, return only the hostname part of the fully qualified domain name for local hosts.
    * NI_NUMERICHOST: If set, then the numeric form of the hostname is returned. (When not set, this will still happen in case the node's name cannot be determined.)
    * NI_NUMERICSERV: If set, then the numeric form of the service address is returned. (When not set, this will still happen in case the service's name cannot be determined.)

    :param flags: the modifer flags
    """
    if (flags & socket.NI_NAMEREQD) and (flags & socket.NI_NUMERICHOST):
        # Conflicting flags.  Punt.
        raise socket.gaierror((socket.EAI_NONAME, 'Name or service not known'))

    resolved = Event()

    def _resolve_callback(result, errorno):
        try:
            if errorno:
                e = pycares.errno.errorcode[errorno]
                msg = pycares.errno.strerror(errorno)
                resolved.send_exception(socket.gaierror(e, msg))
            else:
                resolved.send(result)
        except Exception, e:
            resolved.send_exception(e)

    resolver.getnameinfo(addr, flags, _resolve_callback)
    res = resolved.wait()
    return res.node, res.service





def resolve_address(address):
    """
    Resolve an address (as a tuple) to a valid IP and port
    :param address: a tuple with a hostname or IP and port
    :return: a valid IP and port tuple
    """
    hostname, port = address
    if len(hostname) == 0:
        ip = '0.0.0.0'
    else:
        ip = resolve(hostname)[0]

    assert isinstance(ip, str)
    assert isinstance(port, int)

    return ip, port
