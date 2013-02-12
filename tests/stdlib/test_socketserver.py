#!/usr/bin/env python

from evy import patcher
from evy.patched import SocketServer
from evy.patched import socket
from evy.patched import select
from evy.patched import time
from evy.patched import threading

# to get past the silly 'requires' check
from test import test_support

test_support.use_resources = ['network']

patcher.inject('test.test_socketserver',
               globals(),
               ('SocketServer', SocketServer),
               ('socket', socket),
               ('select', select),
               ('time', time),
               ('threading', threading))

# only a problem with pyevent
from evy import tests

if tests.using_pyevent():
    try:
        SocketServerTest.test_ForkingUDPServer = lambda *a, **kw: None
        SocketServerTest.test_ForkingTCPServer = lambda *a, **kw: None
        SocketServerTest.test_ForkingUnixStreamServer = lambda *a, **kw: None
    except (NameError, AttributeError):
        pass

if __name__ == "__main__":
    test_main()
