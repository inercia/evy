from evy import patcher
from evy.patched import socket
from evy.patched import time

patcher.inject('test.test_timeout',
               globals(),
               ('socket', socket),
               ('time', time))

# to get past the silly 'requires' check
from test import test_support

test_support.use_resources = ['network']

if __name__ == "__main__":
    test_main()
