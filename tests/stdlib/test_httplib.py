from evy import patcher
from evy.patched import httplib
from evy.patched import socket

patcher.inject('test.test_httplib',
               globals(),
               ('httplib', httplib),
               ('socket', socket))

if __name__ == "__main__":
    test_main()
