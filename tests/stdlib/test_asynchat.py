from evy import patcher
from evy.patched import asyncore
from evy.patched import asynchat
from evy.patched import socket
from evy.patched import thread
from evy.patched import threading
from evy.patched import time

patcher.inject("test.test_asynchat",
               globals(),
    ('asyncore', asyncore),
    ('asynchat', asynchat),
    ('socket', socket),
    ('thread', thread),
    ('threading', threading),
    ('time', time))

if __name__ == "__main__":
    test_main()
