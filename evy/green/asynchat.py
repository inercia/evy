from evy import patcher
from evy.green import asyncore
from evy.green import socket

patcher.inject('asynchat',
               globals(),
    ('asyncore', asyncore),
    ('socket', socket))

del patcher
