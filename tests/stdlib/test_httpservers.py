from evy import patcher

from evy.green import BaseHTTPServer
from evy.green import SimpleHTTPServer
from evy.green import CGIHTTPServer
from evy.green import urllib
from evy.green import httplib
from evy.green import threading

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
