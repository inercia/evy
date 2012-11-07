"""Compare spawn to spawn_n"""

import evy
import benchmarks

def cleanup ():
    evy.sleep(0.2)

iters = 10000
best = benchmarks.measure_best(5, iters,
                               'pass',
                               cleanup,
                               evy.sleep)
print "evy.sleep (main)", best[evy.sleep]

gt = evy.spawn(benchmarks.measure_best, 5, iters,
                    'pass',
                    cleanup,
                    evy.sleep)
best = gt.wait()
print "evy.sleep (gt)", best[evy.sleep]

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
print "evy.spawn", best[run_spawn]
print "evy.spawn_n", best[run_spawn_n]
print "evy.spawn_n(**kw)", best[run_spawn_n_kw]
print "%% %0.1f" % ((best[run_spawn] - best[run_spawn_n]) / best[run_spawn_n] * 100)

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
print "evy.GreenPool.spawn", best[run_pool_spawn]
print "evy.GreenPool.spawn_n", best[run_pool_spawn_n]
print "%% %0.1f" % ((best[run_pool_spawn] - best[run_pool_spawn_n]) / best[run_pool_spawn_n] * 100)
