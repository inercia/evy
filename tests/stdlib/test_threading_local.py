from evy import patcher
from evy.patched import thread
from evy.patched import threading
from evy.patched import time

# hub requires initialization before test can run
from evy import hubs

hubs.get_hub()

patcher.inject('test.test_threading_local',
               globals(),
    ('time', time),
    ('thread', thread),
    ('threading', threading))

if __name__ == '__main__':
    test_main()
