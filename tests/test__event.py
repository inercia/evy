import unittest
from evy.event import Event
from evy.api import spawn, sleep, with_timeout
import evy
from tests import LimitedTestCase

DELAY = 0.01

class TestEvent(LimitedTestCase):
    def test_send_exc (self):
        log = []
        e = Event()

        def waiter ():
            try:
                result = e.wait()
                log.append(('received', result))
            except Exception, ex:
                log.append(('catched', ex))

        spawn(waiter)
        sleep(0) # let waiter to block on e.wait()
        obj = Exception()
        e.send(exc = obj)
        sleep(0)
        sleep(0)
        assert log == [('catched', obj)], log

    def test_send (self):
        event1 = Event()
        event2 = Event()

        spawn(event1.send, 'hello event1')
        evy.Timeout(0, ValueError('interrupted'))
        try:
            result = event1.wait()
        except ValueError:
            X = object()
            result = with_timeout(DELAY, event2.wait, timeout_value = X)
            assert result is X, 'Nobody sent anything to event2 yet it received %r' % (result, )


if __name__ == '__main__':
    unittest.main()
