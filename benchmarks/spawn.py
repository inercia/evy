"""Compare spawn to spawn_n"""

import benchmarks


class BenchResults(object):
    sleep_main  = None
    sleep_gt  = None
    spawn = None
    spawn_n = None
    spawn_n_kw = None
    pool_spawn = None
    pool_spawn_n = None


def percent(x, y):
    return (x - y) / y * 100.0

pool = None
iters = 10000

def bench_spawn_evy():
    from evy.green.threads import spawn, spawn_n, sleep
    from evy.green.pools import GreenPool

    print
    print "evy tests:"
    print "----------"

    results = BenchResults()

    def cleanup (): sleep(0.2)

    best = benchmarks.measure_best(5, iters, 'pass', cleanup, sleep)
    results.sleep_main = best[sleep]
    print "evy.sleep (main)", results.sleep_main

    gt = spawn(benchmarks.measure_best, 5, iters, 'pass', cleanup, sleep)
    best = gt.wait()
    results.sleep_gt = best[sleep]
    print "evy.sleep (gt)", results.sleep_gt

    def dummy (i = None): return i
    def run_spawn (): spawn(dummy, 1)
    def run_spawn_n (): spawn_n(dummy, 1)
    def run_spawn_n_kw (): spawn_n(dummy, i = 1)

    best = benchmarks.measure_best(5, iters, 'pass', cleanup, run_spawn_n, run_spawn, run_spawn_n_kw)
    results.spawn = best[run_spawn]
    print "evy.spawn", results.spawn

    results.spawn_n = best[run_spawn_n]
    print "evy.spawn_n", results.spawn_n

    results.spawn_n_kw = best[run_spawn_n_kw]
    print "evy.spawn_n(**kw)", results.spawn_n_kw

    print "evy spawn/spawn_n difference %% %0.1f" % percent(best[run_spawn], best[run_spawn_n])


    def setup ():
        global pool
        pool = GreenPool(iters)

    def run_pool_spawn ():
        pool.spawn(dummy, 1)

    def run_pool_spawn_n ():
        pool.spawn_n(dummy, 1)

    def cleanup_pool ():
        pool.waitall()

    best = benchmarks.measure_best(3, iters, setup, cleanup_pool, run_pool_spawn, run_pool_spawn_n,)

    results.pool_spawn = best[run_pool_spawn]
    print "evy.GreenPool.spawn", results.pool_spawn

    results.pool_spawn_n = best[run_pool_spawn_n]
    print "evy.GreenPool.spawn_n", results.pool_spawn_n

    print "evy spawn/spawn_n difference: %% %0.1f" % percent(best[run_pool_spawn], best[run_pool_spawn_n])
    return results

def bench_spawn_eventlet():
    from eventlet import sleep, spawn, spawn_n, GreenPool

    print
    print "eventlet tests:"
    print "---------------"

    results = BenchResults()

    def cleanup (): sleep(0.2)

    best = benchmarks.measure_best(5, iters, 'pass', cleanup, sleep)
    results.sleep_main = best[sleep]
    print "eventlet.sleep (main)", results.sleep_main

    gt = spawn(benchmarks.measure_best, 5, iters, 'pass', cleanup, sleep)
    best = gt.wait()
    results.sleep_gt = best[sleep]
    print "eventlet.sleep (gt)", results.sleep_gt

    def dummy (i = None): return i
    def run_spawn (): spawn(dummy, 1)
    def run_spawn_n (): spawn_n(dummy, 1)
    def run_spawn_n_kw (): spawn_n(dummy, i = 1)

    best = benchmarks.measure_best(5, iters, 'pass', cleanup, run_spawn_n, run_spawn, run_spawn_n_kw)
    results.spawn = best[run_spawn]
    print "eventlet.spawn", results.spawn

    results.spawn_n = best[run_spawn_n]
    print "eventlet.spawn_n", results.spawn_n

    results.spawn_n_kw = best[run_spawn_n_kw]
    print "eventlet.spawn_n(**kw)", results.spawn_n_kw

    print "eventlet spawn/spawn_n difference %% %0.1f" % percent(best[run_spawn], best[run_spawn_n])


    def setup ():
        global pool
        pool = GreenPool(iters)

    def run_pool_spawn ():
        pool.spawn(dummy, 1)

    def run_pool_spawn_n ():
        pool.spawn_n(dummy, 1)

    def cleanup_pool ():
        pool.waitall()

    best = benchmarks.measure_best(3, iters, setup, cleanup_pool, run_pool_spawn, run_pool_spawn_n,)
    results.pool_spawn = best[run_pool_spawn]
    print "eventlet.GreenPool.spawn", results.pool_spawn

    results.pool_spawn_n = best[run_pool_spawn_n]
    print "eventlet.GreenPool.spawn_n", results.pool_spawn_n

    print "eventlet spawn/spawn_n difference: %% %0.1f" % percent(best[run_pool_spawn], best[run_pool_spawn_n])
    return results



print
print "measuring results for %d iterations" % iters
print

res_evy = bench_spawn_evy()

try:
    res_eventlet = bench_spawn_eventlet()
except ImportError:
    pass
else:
    print
    print "differences (higher is worse)"
    print "-----------------------------"
    print "sleep (main) ",     percent(res_evy.sleep_main,   res_eventlet.sleep_main)
    print "sleep (gt)",        percent(res_evy.sleep_gt,     res_eventlet.sleep_gt)
    print "spawn",             percent(res_evy.spawn,        res_eventlet.spawn)
    print "spawn_n ",          percent(res_evy.spawn_n,      res_eventlet.spawn_n)
    print "spawn_n (**kw)",    percent(res_evy.spawn_n_kw,   res_eventlet.spawn_n_kw)
    print "GreenPool.spawn",   percent(res_evy.pool_spawn,   res_eventlet.pool_spawn)
    print "GreenPool.spawn_n", percent(res_evy.pool_spawn_n, res_eventlet.pool_spawn_n)


