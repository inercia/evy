from evy import patcher
from evy.green import BaseHTTPServer
from evy.green import urllib

patcher.inject('SimpleHTTPServer',
               globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('urllib', urllib))

del patcher

if __name__ == '__main__':
    test()
