#!/usr/bin/env python


import sys

from setuptools import find_packages
from distutils.core import setup

from setup_libuv import libuv_build_ext, libuv_sdist, libuv_extension

from evy import __version__
from os import path

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

    ext_package         = 'evy.uv',              # must match the package defined in the CFFI verify()
    ext_modules         = [libuv_extension],

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

