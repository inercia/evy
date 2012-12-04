from evy import patcher

from evy.patched import BaseHTTPServer
from evy.patched import SimpleHTTPServer
from evy.patched import CGIHTTPServer
from evy.patched import urllib
from evy.patched import httplib
from evy.patched import threading

patcher.inject('test.test_httpservers',
               globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('SimpleHTTPServer', SimpleHTTPServer),
    ('CGIHTTPServer', CGIHTTPServer),
    ('urllib', urllib),
    ('httplib', httplib),
    ('threading', threading))

if __name__ == "__main__":
    test_main()
