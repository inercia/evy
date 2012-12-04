from evy import patcher

from evy.patched import BaseHTTPServer
from evy.patched import threading
from evy.patched import socket
from evy.patched import urllib2

patcher.inject('test.test_urllib2_localnet',
               globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('threading', threading),
    ('socket', socket),
    ('urllib2', urllib2))

if __name__ == "__main__":
    test_main()
