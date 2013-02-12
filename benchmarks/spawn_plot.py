#!/usr/bin/env python
"""
Compare spawn to spawn_n, among other things.

This script will generate a number of "properties" files for the Hudson plot plugin


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

import os
import evy
import benchmarks

DATA_DIR = 'plot_data'

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def write_result (filename, best):
    fd = open(os.path.join(DATA_DIR, filename), 'w')
    fd.write('YVALUE=%s' % best)
    fd.close()


def cleanup ():
    evy.sleep(0.2)

iters = 10000
best = benchmarks.measure_best(5, iters,
                               'pass',
                               cleanup,
                               evy.sleep)

write_result('evy.sleep_main', best[evy.sleep])

gt = evy.spawn(benchmarks.measure_best, 5, iters,
                    'pass',
                    cleanup,
                    evy.sleep)
best = gt.wait()
write_result('evy.sleep_gt', best[evy.sleep])

def dummy (i = None):
    return i


def run_spawn ():
    evy.spawn(dummy, 1)


def run_spawn_n ():
    evy.spawn_n(dummy, 1)


def run_spawn_n_kw ():
    evy.spawn_n(dummy, i = 1)


best = benchmarks.measure_best(5, iters,
                               'pass',
                               cleanup,
                               run_spawn_n,
                               run_spawn,
                               run_spawn_n_kw)
write_result('evy.spawn', best[run_spawn])
write_result('evy.spawn_n', best[run_spawn_n])
write_result('evy.spawn_n_kw', best[run_spawn_n_kw])

pool = None

def setup ():
    global pool
    pool = evy.GreenPool(iters)


def run_pool_spawn ():
    pool.spawn(dummy, 1)


def run_pool_spawn_n ():
    pool.spawn_n(dummy, 1)


def cleanup_pool ():
    pool.waitall()


best = benchmarks.measure_best(3, iters,
                               setup,
                               cleanup_pool,
                               run_pool_spawn,
                               run_pool_spawn_n,
                               )
write_result('evy.GreenPool.spawn', best[run_pool_spawn])
write_result('evy.GreenPool.spawn_n', best[run_pool_spawn_n])
