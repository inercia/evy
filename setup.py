#!/usr/bin/env python


import sys

from setuptools import find_packages
from distutils.core import setup

from setup_libuv import libuv_build_ext, libuv_sdist

from evy import __version__
from os import path

# in order to build with CFFI, you must import at least the module(s) that define the ffi's
# that you use in your application
try:
    import evy.hubs.libuv
except ImportError:
    print "FATAL ERROR: you need the CFFI module installed in your system"
    sys.exit(1)


setup(
    name                = 'evy',
    version             = __version__,
    description         = 'Highly concurrent networking library for Pypy',
    author              = 'Alvaro Saurin',
    author_email        = 'alvaro.saurin@gmail.com',
    url                 = 'http://github.com/inercia/evy',

    packages            = find_packages(exclude = ['tests', 'benchmarks']),
    install_requires    = [],
    zip_safe            = False,

    long_description    = open(
        path.join(
            path.dirname(__file__),
            'README'
        )
    ).read(),

    cmdclass            = {'build_ext': libuv_build_ext,
                           'sdist'    : libuv_sdist},

    ext_modules         = [evy.hubs.libuv.ffi.verifier.get_extension()],

    test_suite          = 'nose.collector',
    tests_require       = 'httplib2',

    classifiers         = [
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 2.4",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta"]
)

