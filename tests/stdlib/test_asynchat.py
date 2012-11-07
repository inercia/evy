from evy import patcher
from evy.green import asyncore
from evy.green import asynchat
from evy.green import socket
from evy.green import thread
from evy.green import threading
from evy.green import time

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
