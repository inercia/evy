Basic Usage
=============

If it's your first time to Evy, you may find the illuminated examples in the
:ref:`design-patterns` document to be a good starting point.

Evy is built around the concept of green threads (i.e. coroutines, we use the
terms interchangeably) that are launched to do network-related work. Green
threads differ from normal threads in two main ways:

* Green threads are so cheap they are nearly free.  You do not have to conserve
  green threads like you would normal threads.  In general, there will be at
  least one green thread per network connection.
* Green threads cooperatively yield to each other instead of preemptively being
  scheduled.  The major advantage from this behavior is that shared data structures
  don't need locks, because only if a yield is explicitly called can another
  green thread have access to the data structure.  It is also possible to inspect
  primitives such as queues to see if they have any pending data.

Primary API
===========

The design goal for Evy's API is simplicity and readability. You should be able
to read its code and understand what it's doing. Fewer lines of code are preferred
over excessively clever implementations.
`Like Python itself <http://www.python.org/dev/peps/pep-0020/>`_, there should
be one, and only one obvious way to do it in Evy!

Though Evy has many modules, much of the most-used stuff is accessible simply
by doing ``import evy``. Here's a quick summary of the functionality available
in the ``evy`` module, with links to more verbose documentation on each.

Greenthread Spawn
-----------------------

.. function:: evy.spawn(func, *args, **kw)
   
   This launches a greenthread to call *func*.  Spawning off multiple greenthreads
   gets work done in parallel.  The return value from ``spawn`` is a
   :class:`greenthread.GreenThread` object, which can be used to retrieve the
   return value of *func*.  See :func:`spawn <evy.green.threads.spawn>` for
   more details.
   
.. function:: evy.spawn_n(func, *args, **kw)
   
   The same as :func:`spawn`, but it's not possible to know how the function
   terminated (i.e. no return value or exceptions).  This makes execution faster.
   See :func:`spawn_n <evy.green.threads.spawn_n>` for more details.

.. function:: evy.spawn_after(seconds, func, *args, **kw)
   
   Spawns *func* after *seconds* have elapsed; a delayed version of :func:`spawn`.
   To abort the spawn and prevent *func* from being called, call
   :meth:`GreenThread.cancel` on the return value of :func:`spawn_after`.  See
   :func:`spawn_after <evy.green.threads.spawn_after>` for more details.

Greenthread Control
-----------------------

.. function:: evy.sleep(seconds=0)

   Suspends the current greenthread and allows others a chance to process.  See
   :func:`sleep <evy.green.threads.sleep>` for more details.

.. class:: evy.GreenPool

   Pools control concurrency. It's very common in applications to want to
   consume only a finite amount of memory, or to restrict the amount of connections
   that one part of the code holds open so as to leave more for the rest, or
   to behave consistently in the face of unpredictable input data. GreenPools
   provide this control.  See :class:`GreenPool <evy.greep.pools.GreenPool>`
   for more on how to use these.

.. class:: evy.GreenPile

   GreenPile objects represent chunks of work. In essence a GreenPile is an
   iterator that can be stuffed with work, and the results read out later.
   See :class:`GreenPile <evy.greep.pools.GreenPile>` for more details.
    
.. class:: evy.Queue

   Queues are a fundamental construct for communicating data between execution
   units. Evy's Queue class is used to communicate between greenthreads, and
   provides a bunch of useful features for doing that.  See
   :class:`Queue <evy.queue.Queue>` for more details.
    
.. class:: evy.Timeout

   This class is a way to add timeouts to anything. It raises *exception* in
   the current greenthread after *timeout* seconds.  When *exception* is omitted
   or ``None``, the Timeout instance itself is raised.
    
   Timeout objects are context managers, and so can be used in with statements.
   See :class:`Timeout <evy.timeout.Timeout>` for more details.

Patching Functions
---------------------
    
.. function:: evy.import_patched(modulename, *additional_modules, **kw_additional_modules)

   Imports a module in a way that ensures that the module uses "green" versions
   of the standard library modules, so that everything works nonblockingly.
   The only required argument is the name of the module to be imported.  For
   more information see :ref:`import-green`.

.. function:: evy.monkey_patch(all=True, os=False, select=False, socket=False, thread=False, time=False)

   Globally patches certain system modules to be greenthread-friendly. The
   keyword arguments afford some control over which modules are patched. If
   *all* is True, then all modules are patched regardless of the other arguments.
   If it's False, then the rest of the keyword arguments control patching of
   specific subsections of the standard library.  Most patch the single module
   of the same name (os, time, select).  The exceptions are socket, which also
   patches the ssl module if present; and thread, which patches thread, threading,
   and Queue.  It's safe to call monkey_patch multiple times. For more information
   see :ref:`monkey-patch`.

Network Convenience Functions
------------------------------

.. autofunction:: evy.connect

.. autofunction:: evy.listen

.. autofunction:: evy.wrap_ssl

.. autofunction:: evy.serve

.. autoclass:: evy.StopServe
    
These are the basic primitives of Evy; there are a lot more out there in the
other Evy modules; check out the :doc:`modules`.

