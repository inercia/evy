"""Integrate evy with twisted's reactor mainloop.

You generally don't have to use it unless you need to call reactor.run()
yourself.
"""
from evy.hubs.twistedr import BaseTwistedHub
from evy.support import greenlets as greenlet
from evy.hubs import _threadlocal, use_hub

use_hub(BaseTwistedHub)
assert not hasattr(_threadlocal, 'hub')
hub = _threadlocal.hub = _threadlocal.Hub(greenlet.getcurrent())
