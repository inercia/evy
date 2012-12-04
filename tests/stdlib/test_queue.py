from evy import patcher
from evy.patched import Queue
from evy.patched import threading
from evy.patched import time

patcher.inject('test.test_queue',
               globals(),
    ('Queue', Queue),
    ('threading', threading),
    ('time', time))

if __name__ == "__main__":
    test_main()
