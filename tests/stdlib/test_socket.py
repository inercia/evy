#!/usr/bin/env python

from evy import patcher
from evy.green import socket
from evy.green import select
from evy.green import time
from evy.green import thread
from evy.green import threading

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
