"""
Test timer adds & expires on hubs.hub.BaseHub

Profiling and graphs
====================

You can profile this program and obtain a call graph with `gprof2dot` and `graphviz`:

```
python -m cProfile -o output.pstats    path/to/this/script arg1 arg2
gprof2dot.py -f pstats output.pstats | dot -Tpng -o output.png
```

It generates a graph where a node represents a function and has the following layout:

```
    +------------------------------+
    |        function name         |
    | total time % ( self time % ) |
    |         total calls          |
    +------------------------------+
```

where:

  * total time % is the percentage of the running time spent in this function and all its children;
  * self time % is the percentage of the running time spent in this function alone;
  * total calls is the total number of times this function was called (including recursive calls).

An edge represents the calls between two functions and has the following layout:

```
               total time %
                  calls
    parent --------------------> children
```

where:

  * total time % is the percentage of the running time transfered from the children to this parent (if available);
  * calls is the number of calls the parent function called the children.

"""


import sys
import evy
import random
import time

from evy.hubs import timer, get_hub

timer_count = 100000

if len(sys.argv) >= 2:
    timer_count = int(sys.argv[1])

l = []

def work (n):
    l.append(n)

timeouts = [random.uniform(0, 10) for x in xrange(timer_count)]

hub = get_hub()

start = time.time()

scheduled = []

for timeout in timeouts:
    t = timer.Timer(timeout, work, timeout)
    t.schedule()

    scheduled.append(t)

hub.prepare_timers()
hub.fire_timers(time.time() + 11)
hub.prepare_timers()

end = time.time()

print "Duration: %f" % (end - start,)
