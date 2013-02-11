Evy is a concurrency library, based on eventlet, and using libuv in its core.

Quick Example
=============

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

Documentation
=============

You can checkout evy's documentation at

https://evy.readthedocs.org/en/latest/index.html

Or, if you want to build a local copy of the HTML docs, you must have Sphinx,
(which can be found at http://sphinx.pocoo.org/ or installed with `easy_install sphinx`)
and then run:

    make docs

The built html files can be found in `doc/_build/html` afterwards...

Status
======

The basic unit tests functionality is implemented, but it cannot fully replace the standard
patched modules yet (ie, there are some differences in error codes or exceptions thrown...)

