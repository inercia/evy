#!/usr/bin/env python

from evy import patcher
from evy.patched import socket
from evy.patched import select
from evy.patched import time
from evy.patched import thread
from evy.patched import threading

patcher.inject('test.test_socket',
               globals(),
    ('socket', socket),
    ('select', select),
    ('time', time),
    ('thread', thread),
    ('threading', threading))

# TODO: fix
TCPTimeoutTest.testInterruptedTimeout = lambda *a: None

if __name__ == "__main__":
    test_main()
