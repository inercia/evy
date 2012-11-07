from evy import patcher
from evy.green import select
from evy.green import socket
from evy.green import time

patcher.inject("asyncore",
               globals(),
    ('select', select),
    ('socket', socket),
    ('time', time))

del patcher
