.. _understanding_hubs:

Understanding Evy Hubs
===========================

A hub forms the basis of Evy's event loop, which dispatches I/O events and schedules greenthreads.
It is the existence of the hub that promotes coroutines (which can be tricky to program with) into
greenthreads (which are easy).

Evy has only one hub implementation, the libuv one, and when you start using it.

How the Hubs Work
-----------------

The hub has a main greenlet, MAINLOOP.  When one of the running coroutines needs
to do some I/O, it registers a listener with the hub (so that the hub knows when to wake it up
again), and then switches to MAINLOOP (via ``get_hub().switch()``).  If there are other coroutines
that are ready to run, MAINLOOP switches to them, and when they complete or need to do more I/O,
they switch back to the MAINLOOP.  In this manner, MAINLOOP ensures that every coroutine gets
scheduled when it has some work to do.

MAINLOOP is launched only when the first I/O operation happens, and it is not the same greenlet
that __main__ is running in.  This lazy launching is why it's not necessary to explicitly call a
dispatch() method like other frameworks, which in turn means that code can start using Evy without
needing to be substantially restructured.

More Hub-Related Functions
---------------------------

.. autofunction:: evy.hubs.get_hub
.. autofunction:: evy.hubs.get_default_hub
.. autofunction:: evy.hubs.trampoline

