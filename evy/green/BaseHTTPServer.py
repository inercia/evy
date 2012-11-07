from evy import patcher
from evy.green import socket
from evy.green import SocketServer

patcher.inject('BaseHTTPServer',
               globals(),
    ('socket', socket),
    ('SocketServer', SocketServer))

del patcher

if __name__ == '__main__':
    test()
