#!/usr/bin/env python
'''
    Compare spawn to spawn_n, among other things.

    This script will generate a number of "properties" files for the
    Hudson plot plugin
'''

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
