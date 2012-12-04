from evy import patcher
from evy.patched import subprocess
from evy.patched import time

patcher.inject('test.test_subprocess',
               globals(),
    ('subprocess', subprocess),
    ('time', time))

if __name__ == "__main__":
    test_main()
