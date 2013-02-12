"""
Benchmark evaluating evy's performance at speaking to itself over a localhost socket.

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

import time
import benchmarks

import socket as socket_orig



BYTES = 1000
SIZE = 1
CONCURRENCY = 50
TRIES = 5




def reader (sock):
    expect = BYTES
    while expect > 0:
        d = sock.recv(min(expect, SIZE))
        expect -= len(d)


def writer (addr, socket_impl):
    sock = socket_impl(socket_orig.AF_INET, socket_orig.SOCK_STREAM)
    sock.connect(addr)
    sent = 0
    while sent < BYTES:
        d = 'xy' * (max(min(SIZE / 2, BYTES - sent), 1))
        sock.sendall(d)
        sent += len(d)


####################################################################################################


def launch_green_threads ():
    from evy.patched import socket
    import evy

    def green_accepter (server_sock, pool):
        for i in xrange(CONCURRENCY):
            sock, addr = server_sock.accept()
            pool.spawn_n(reader, sock)

    pool = evy.GreenPool(CONCURRENCY * 2 + 1)
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('localhost', 0))
    server_sock.listen(50)
    addr = ('localhost', server_sock.getsockname()[1])
    pool.spawn_n(green_accepter, server_sock, pool)
    for i in xrange(CONCURRENCY):
        pool.spawn_n(writer, addr, socket.socket)
    pool.waitall()


def launch_heavy_threads ():
    import threading
    import socket

    def heavy_accepter (server_sock, pool):
        import threading
        for i in xrange(CONCURRENCY):
            sock, addr = server_sock.accept()
            t = threading.Thread(None, reader, "reader thread", (sock,))
            t.start()
            pool.append(t)

    threads = []
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('localhost', 0))
    server_sock.listen(50)
    addr = ('localhost', server_sock.getsockname()[1])
    accepter_thread = threading.Thread(None, heavy_accepter, "accepter thread",
        (server_sock, threads))
    accepter_thread.start()
    threads.append(accepter_thread)
    for i in xrange(CONCURRENCY):
        client_thread = threading.Thread(None, writer, "writer thread", (addr, socket.socket))
        client_thread.start()
        threads.append(client_thread)
    for t in threads:
        t.join()


if __name__ == "__main__":
    import optparse

    parser = optparse.OptionParser()
    parser.add_option('--compare-threading', action = 'store_true', dest = 'threading',
                      default = False)
    parser.add_option('-b', '--bytes', type = 'int', dest = 'bytes',
                      default = BYTES)
    parser.add_option('-s', '--size', type = 'int', dest = 'size',
                      default = SIZE)
    parser.add_option('-c', '--concurrency', type = 'int', dest = 'concurrency',
                      default = CONCURRENCY)
    parser.add_option('-t', '--tries', type = 'int', dest = 'tries',
                      default = TRIES)

    opts, args = parser.parse_args()

    BYTES = opts.bytes
    SIZE = opts.size
    CONCURRENCY = opts.concurrency

    funcs = [launch_green_threads]
    if opts.threading:
        funcs.append(launch_heavy_threads)

    print
    print "measuring results for %d iterations..." % opts.tries
    print

    results = benchmarks.measure_best(opts.tries, 3, lambda: None, lambda: None, *funcs)

    print "green:", results[launch_green_threads]
    if opts.threading:
        print "threads:", results[launch_heavy_threads]
        print "%", ((results[launch_green_threads] - results[launch_heavy_threads]) /
                    (results[launch_heavy_threads] * 100))

