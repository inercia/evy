version_info = (0, 0, 1, "dev")
__version__ = ".".join(map(str, version_info))

try:
    from evy import greenthread
    from evy import greenpool
    from evy import queue
    from evy import timeout
    from evy import patcher
    from evy import convenience
    import greenlet

    sleep = greenthread.sleep
    spawn = greenthread.spawn
    spawn_n = greenthread.spawn_n
    spawn_after = greenthread.spawn_after
    kill = greenthread.kill

    Timeout = timeout.Timeout
    with_timeout = timeout.with_timeout

    GreenPool = greenpool.GreenPool
    GreenPile = greenpool.GreenPile

    Queue = queue.Queue

    import_patched = patcher.import_patched
    monkey_patch = patcher.monkey_patch

    connect = convenience.connect
    listen = convenience.listen
    serve = convenience.serve
    StopServe = convenience.StopServe
    wrap_ssl = convenience.wrap_ssl

    getcurrent = greenlet.greenlet.getcurrent

except ImportError, e:
    # This is to make Debian packaging easier, it ignores import
    # errors of greenlet so that the packager can still at least
    # access the version.  Also this makes easy_install a little quieter
    if 'greenlet' not in str(e):
        # any other exception should be printed
        import traceback

        traceback.print_exc()
