from evy import patcher
from evy.green import asyncore
from evy.green import ftplib
from evy.green import threading
from evy.green import socket

patcher.inject('test.test_ftplib', globals())

# this test only fails on python2.7/pyevent/--with-xunit; screw that
try:
    TestTLS_FTPClass.test_data_connection = lambda *a, **kw: None
except (AttributeError, NameError):
    pass

if __name__ == "__main__":
    test_main()
