from evy import patcher
from evy.green import httplib
from evy.green import urllib

patcher.inject('test.test_urllib',
               globals(),
    ('httplib', httplib),
    ('urllib', urllib))

if __name__ == "__main__":
    test_main()
