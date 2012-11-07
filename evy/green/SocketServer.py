from evy import patcher

from evy.green import socket
from evy.green import select
from evy.green import threading

patcher.inject('SocketServer',
               globals(),
    ('socket', socket),
    ('select', select),
    ('threading', threading))

# QQQ ForkingMixIn should be fixed to use green waitpid?
