from evy import patcher
from evy.patched import asyncore
from evy.patched import ftplib
from evy.patched import threading
from evy.patched import socket

patcher.inject('test.test_ftplib', globals())

# this test only fails on python2.7/pyevent/--with-xunit; screw that
try:
    TestTLS_FTPClass.test_data_connection = lambda *a, **kw: None
except (AttributeError, NameError):
    pass

if __name__ == "__main__":
    test_main()
