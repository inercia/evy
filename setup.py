#!/usr/bin/env python


import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


__HERE__ = os.path.dirname(__file__)

__VERSION_FILE__ = os.path.join(__HERE__, 'VERSION')
__VERSION__ = open(__VERSION_FILE__).read().strip()

__README_FILE__ = os.path.join(__HERE__, 'README.md')

## note: do not import anything from evy or it will try to build the CFFI stuff...


setup(
    name                = 'evy',
    version             = '0.1',
    description         = 'Highly concurrent networking library for Pypy',
    author              = 'Alvaro Saurin',
    author_email        = 'alvaro.saurin@gmail.com',
    url                 = 'http://github.com/inercia/evy',

    packages            = find_packages(exclude = ['tests', 'benchmarks']),

    install_requires    = ['setuptools',
                           'dnspython',
                           'pyuv',
                           'pycares',
    ],
    zip_safe            = False,

    long_description    = open(__README_FILE__).read(),

    ext_package         = 'evy',              # must match the package defined in the CFFI verify()

    test_suite          = 'nose.collector',
    tests_require       = ['nose',
                           'httplib2'],

   entry_points = {
        'console_scripts': [
            'evy-profiler = evy.tools.profiler:main'
        ]
    },
    
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

