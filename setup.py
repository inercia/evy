#!/usr/bin/env python


try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


from os import path


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

    long_description    = open(
        path.join(
            path.dirname(__file__),
            'README'
        )
    ).read(),

    ext_package         = 'evy',              # must match the package defined in the CFFI verify()

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

