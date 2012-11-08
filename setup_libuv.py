#!/usr/bin/env python
"""gevent build & installation script"""
import sys
import os
import platform
from os.path import join, abspath, basename, dirname
from glob import glob

try:
    from setuptools import Extension, setup
except ImportError:
    from distutils.core import Extension, setup

from distutils.command.build_ext import build_ext
from distutils.command.sdist import sdist as _sdist
from distutils.errors import CCompilerError, DistutilsExecError, DistutilsPlatformError
ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError, IOError)


__here__ = os.path.dirname(__file__)

LIBUV_DIR = os.path.join(__here__, 'libuv')

def _system(cmd):
    cmd = ' '.join(cmd)
    sys.stdout.write('Running %r in %s\n' % (cmd, os.getcwd()))
    return os.system(cmd)



def make(done=[]):
    print 'making libuv'

    if not done:
        if os.path.exists(os.path.join(LIBUV_DIR, 'Makefile')):
            if "PYTHON" not in os.environ:
                os.environ["PYTHON"] = sys.executable
            if sys.platform == "darwin":
                prev_flags = os.environ.get("CFLAGS", "")
                os.environ["CFLAGS"] = ("%s %s" % (prev_flags, "-U__llvm__ -arch x86_64 -arch i386")).lstrip()
            if os.system('make -C %s' % LIBUV_DIR):
                sys.exit(1)
        else:
            print 'ERROR: no Makefile found'
        done.append(1)


class libuv_sdist(_sdist):

    def run(self):
        renamed = False
        if os.path.exists('Makefile'):
            make()
            os.rename('Makefile', 'Makefile.ext')
            renamed = True
        try:
            return _sdist.run(self)
        finally:
            if renamed:
                os.rename('Makefile.ext', 'Makefile')


class libuv_build_ext(build_ext):

    def build_extension(self, ext):
        print 'building libuv extension'
        make()

        try:
            result = build_ext.build_extension(self, ext)
        except ext_errors:
            if getattr(ext, 'optional', False):
                raise BuildFailed
            else:
                raise

        import evy.hubs.libuv
        libuv_modules = [evy.hubs.libuv.ffi.verifier.get_extension()]

        return libuv_modules


libuv_extension = Extension(name='libuv',
                            sources=[])



class BuildFailed(Exception):
    pass