#!/usr/bin/env python



import sys
import os

try:
    from setuptools import Extension, setup
except ImportError:
    from distutils.core import Extension, setup


from distutils.command.build_ext    import build_ext
from distutils.command.sdist        import sdist as _sdist
from distutils.errors               import CCompilerError, DistutilsExecError, DistutilsPlatformError

ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError, IOError)

__here__ = os.path.dirname(__file__)


#: where the libuv is found...
LIBUV_DIR = os.path.join(__here__, 'libuv')



def _system(cmd):
    cmd = ' '.join(cmd)
    sys.stdout.write('Running %r in %s\n' % (cmd, os.getcwd()))
    return os.system(cmd)


def make(done = []):
    """
    Run the make proccess in the libuv directory

    :param done:
    :return:
    """
    print 'making libuv'

    if not done:
        if os.path.exists(os.path.join(LIBUV_DIR, 'Makefile')):
            if "PYTHON" not in os.environ:
                os.environ["PYTHON"] = sys.executable

            new_cflags = ""
            prev_cflags = os.environ.get("CFLAGS", "")

            new_ldflags = ""
            prev_ldflags = os.environ.get("LDFLAGS", "")

            if sys.platform == 'darwin':
                new_cflags = new_cflags + ' -O3 -U__llvm__ -arch x86_64 -arch i386'
                new_ldflags = new_ldflags + ' -framework CoreServices'
            elif sys.platform in ['linux', 'linux2']:
                new_cflags = new_cflags + ' -fPIC '

            c_flags = ("%s %s" % (prev_cflags, new_cflags)).lstrip()
            ld_flags = ("%s %s" % (prev_ldflags, new_ldflags)).lstrip()

            print '... using CFLAGS="%s", LDFLAGS="%s"' % (c_flags, ld_flags)

            if len(c_flags) > 0:    os.environ["CFLAGS"] = c_flags
            if len(ld_flags) > 0:   os.environ["LDFLAGS"] = ld_flags

            if os.system('make -C %s' % LIBUV_DIR):
                sys.exit(1)

            ## reset the env
            os.environ["CFLAGS"] = prev_cflags
            os.environ["LDFLAGS"] = prev_ldflags
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
    """
    Builder for the libuv 'extension'
    """

    def build_extensions(self):
        """
        Runs the builder
        """
        print 'building libuv extension'
        make()

        import evy.uv.interface
        libuv_extension = evy.uv.interface.ffi.verifier.get_extension()
        self.extensions = [libuv_extension]

        print 'using libuv version: %s' % evy.uv.get_version()
        print '(build path: %s)' % self.get_ext_fullpath(libuv_extension.name)



libuv_extension = Extension(name = 'libuv',
                            sources = [])



