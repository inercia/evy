from evy import patcher
from evy.green import ftplib
from evy.green import httplib
from evy.green import socket
from evy.green import time
from evy.green import urllib

patcher.inject('urllib2',
               globals(),
    ('httplib', httplib),
    ('socket', socket),
    ('time', time),
    ('urllib', urllib))

FTPHandler.ftp_open = patcher.patch_function(FTPHandler.ftp_open, ('ftplib', ftplib))

del patcher
