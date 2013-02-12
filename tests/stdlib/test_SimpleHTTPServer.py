from evy import patcher
from evy.patched import SimpleHTTPServer

patcher.inject('test.test_SimpleHTTPServer',
               globals(),
               ('SimpleHTTPServer', SimpleHTTPServer))

if __name__ == "__main__":
    test_main()
