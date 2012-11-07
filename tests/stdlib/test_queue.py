from evy import patcher
from evy.green import Queue
from evy.green import threading
from evy.green import time

patcher.inject('test.test_queue',
               globals(),
    ('Queue', Queue),
    ('threading', threading),
    ('time', time))

if __name__ == "__main__":
    test_main()
