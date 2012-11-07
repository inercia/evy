from evy import patcher
from evy.green import socket

to_patch = [('socket', socket)]

try:
    from evy.green import ssl

    to_patch.append(('ssl', ssl))
except ImportError:
    pass

patcher.inject('httplib',
               globals(),
               *to_patch)

if __name__ == '__main__':
    test()
