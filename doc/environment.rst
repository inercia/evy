.. _env_vars:

Environment Variables
======================

Evy's behavior can be controlled by a few environment variables.
These are only for the advanced user.

EVY_THREADPOOL_SIZE

   The size of the threadpool in :mod:`~evy.tpool`.  This is an
   environment variable because tpool constructs its pool on first
   use, so any control of the pool size needs to happen before then.
