Evy is a concurrency library, based on eventlet, and using libuv in its core.

Quick Example
===============

Here's something you can try right on the command line::

    % python
    >>> from evy.patched import urllib2
    >>> from evy.green.threads import spawn, waitall
    >>> gt1 = spawn(urllib2.urlopen, 'http://facebook.com')
    >>> gt2 = spawn(urllib2.urlopen, 'http://secondlife.com')
    >>> waitall(gt1, gt2)

Read the docs
=============

Check out the latest documentation (here)[http://evy.readthedocs.org/en/latest/].

Building the Docs Locally
=========================

To build a complete set of HTML documentation, you must have Sphinx, which can be found at
http://sphinx.pocoo.org/ (or installed with `easy_install sphinx`)

  make docs
  
The built html files can be found in doc/_build/html afterward.

Status
======

The basic unit tests functionality is implemented, but it cannot fully replace the standard
patched modules yet (ie, there are some differences in error codes or exceptions thrown...)

