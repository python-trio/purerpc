import re
import os
import sys
import subprocess
from multiprocessing import cpu_count
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext

exec(open("src/purerpc/_version.py", encoding="utf-8").read())


def read(*names, **kwargs):
    with open(os.path.join(os.path.dirname(__file__), *names), "r") as fin:
        return fin.read()


class CMakeExtension(Extension):
    def __init__(self, name, cmake_target=None, sourcedir=''):
        super().__init__(name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)
        self.cmake_target = cmake_target


class CMakeBuild(build_ext):
    def run(self):
        self._cmake_cache_paths = set()
        try:
            subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: " +
                ", ".join(e.name for e in self.extensions))
        super().run()

    def build_extension(self, ext):
        if isinstance(ext, CMakeExtension):
            extdir = os.path.abspath(
                os.path.dirname(self.get_ext_fullpath(ext.name)))
            cmake_args = [
                '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                '-DPYTHON_EXECUTABLE=' + sys.executable,
                '-DLIBDECODER_USE_TIMSORT=OFF',
                ]
            debug = self.debug or (os.getenv("DEBUG") is not None)
            if debug:
                print("WARNING: building in Debug mode, this may affect performance")
            else:
                print("Building in Release mode")
            cfg = 'AddressSanitize' if debug else 'Release'
            build_args = ['--config', cfg]
            if ext.cmake_target is not None:
                build_args += ['--target', ext.cmake_target]

            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j' + str(cpu_count())]

            env = os.environ.copy()
            env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(
                env.get('CXXFLAGS', ''),
                self.distribution.get_version())
            if not os.path.exists(self.build_temp):
                os.makedirs(self.build_temp)
            if ext.sourcedir not in self._cmake_cache_paths:
                subprocess.check_call(['cmake', ext.sourcedir] + cmake_args,
                                      cwd=self.build_temp, env=env)
                self._cmake_cache_paths.add(ext.sourcedir)
            subprocess.check_call(['cmake', '--build', '.'] + build_args,
                                  cwd=self.build_temp)
            print()  # Add an empty line for cleaner output
        else:
            super().build_extension(ext)


def main():
    console_scripts = ['protoc-gen-purerpc=purerpc.protoc_plugin.plugin:main']
    setup(
        name="purerpc",
        version=__version__,
        license="Apache License Version 2.0",
        description=("Asynchronous pure Python gRPC client and server implementation "
                     "supporting asyncio, uvloop, curio and trio"),
        long_description='%s\n%s' % (
            re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.md')),
            re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('RELEASE.md'))
        ),
        long_description_content_type='text/markdown',
        author="Andrew Stepanov",
        url="https://github.com/standy66/purerpc",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Intended Audience :: Telecommunications Industry",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: MacOS",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: POSIX :: BSD",
            "Operating System :: POSIX :: Linux",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Framework :: AsyncIO",
            "Framework :: Trio",
            "Framework :: Pytest",
            "Topic :: Internet",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
            "Topic :: Software Development :: Libraries",
            "Topic :: Software Development :: Code Generators",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: System :: Networking",
        ],
        keywords=[
            "async", "await", "grpc", "pure-python", "pypy", "network",
            "rpc", "http2",
        ],
        packages=find_packages('src'),
        package_dir={'': 'src'},
        ext_modules=[
            CMakeExtension("purerpc.grpclib._grpclib_bindings", cmake_target="_grpclib_bindings"),
        ],
        cmdclass=dict(build_ext=CMakeBuild),
        test_suite="tests",
        python_requires=">=3.5",
        install_requires=[
            "h2>=3.1.0,<4",
            "protobuf~=3.6",
            "anyio>=1.0.0b2,<2",
            "async_exit_stack>=1.0.1,<2",
            "tblib>=1.3.2,<2",
            "async_generator>=1.10,<2.0",
            "python-forge~=18.6"
        ],
        entry_points={
            "console_scripts": console_scripts,
        },
        setup_requires=["pytest-runner"],
        tests_require=[
            "pytest",
            "grpcio",
            "grpcio_tools",
            "uvloop",
            "trio>=0.11",
            "curio>=0.9",
        ]
    )


if __name__ == "__main__":
    main()
