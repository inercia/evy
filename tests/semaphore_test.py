import unittest
import evy
from evy import semaphore
from tests import LimitedTestCase

class TestSemaphore(LimitedTestCase):
    def test_bounded (self):
        sem = semaphore.CappedSemaphore(2, limit = 3)
        self.assertEqual(sem.acquire(), True)
        self.assertEqual(sem.acquire(), True)
        gt1 = evy.spawn(sem.release)
        self.assertEqual(sem.acquire(), True)
        self.assertEqual(-3, sem.balance)
        sem.release()
        sem.release()
        sem.release()
        gt2 = evy.spawn(sem.acquire)
        sem.release()
        self.assertEqual(3, sem.balance)
        gt1.wait()
        gt2.wait()

    def test_bounded_with_zero_limit (self):
        sem = semaphore.CappedSemaphore(0, 0)
        gt = evy.spawn(sem.acquire)
        sem.release()
        gt.wait()


if __name__ == '__main__':
    unittest.main()
