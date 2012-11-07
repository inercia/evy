from evy import patcher
from evy.green import BaseHTTPServer
from evy.green import SimpleHTTPServer
from evy.green import urllib
from evy.green import select

test = None # bind prior to patcher.inject to silence pyflakes warning below
patcher.inject('CGIHTTPServer',
               globals(),
    ('BaseHTTPServer', BaseHTTPServer),
    ('SimpleHTTPServer', SimpleHTTPServer),
    ('urllib', urllib),
    ('select', select))

del patcher

if __name__ == '__main__':
    test() # pyflakes false alarm here unless test = None above
