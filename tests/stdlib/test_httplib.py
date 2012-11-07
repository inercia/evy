from evy import patcher
from evy.green import httplib
from evy.green import socket

patcher.inject('test.test_httplib',
               globals(),
    ('httplib', httplib),
    ('socket', socket))

if __name__ == "__main__":
    test_main()
