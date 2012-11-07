from evy import patcher

from evy.green import BaseHTTPServer
from evy.green import threading
from evy.green import socket
from evy.green import urllib2

patcher.inject('test.test_urllib2_localnet',
               globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('threading', threading),
    ('socket', socket),
    ('urllib2', urllib2))

if __name__ == "__main__":
    test_main()
