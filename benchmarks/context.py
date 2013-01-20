"""Test context switching performance of threading and evy"""

import threading
import time

from evy import event
from evy import hubs
from evy.green import threads


CONTEXT_SWITCHES = 100000

def run (event, wait_event):
    counter = 0
    while counter <= CONTEXT_SWITCHES:
        wait_event.wait()
        wait_event.reset()
        counter += 1
        event.send()


def test_evy ():
    event1 = event.Event()
    event2 = event.Event()
    event1.send()
    thread1 = threads.spawn(run, event1, event2)
    thread2 = threads.spawn(run, event2, event1)

    thread1.wait()
    thread2.wait()


class BenchThread(threading.Thread):
    def __init__ (self, event, wait_event):
        threading.Thread.__init__(self)
        self.counter = 0
        self.event = event
        self.wait_event = wait_event

    def run (self):
        while self.counter <= CONTEXT_SWITCHES:
            self.wait_event.wait()
            self.wait_event.clear()
            self.counter += 1
            self.event.set()


def test_thread ():
    event1 = threading.Event()
    event2 = threading.Event()
    event1.set()
    thread1 = BenchThread(event1, event2)
    thread2 = BenchThread(event2, event1)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

print "Testing with %d context switches" % CONTEXT_SWITCHES
start = time.time()
test_thread()
print "threading: %.02f seconds" % (time.time() - start)

hubs.use_hub()
start = time.time()
test_evy()
print "evy hub:   %.02f seconds" % (time.time() - start)


