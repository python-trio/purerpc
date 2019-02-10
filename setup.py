import re
import os
from setuptools import setup, find_packages

exec(open("src/purerpc/_version.py", encoding="utf-8").read())


def read(*names, **kwargs):
    with open(os.path.join(os.path.dirname(__file__), *names), "r") as fin:
        return fin.read()


def main():
    console_scripts = ['protoc-gen-purerpc=purerpc.protoc_plugin.plugin:main']
    setup(
        name="purerpc",
        version=__version__,
        license="Apache License Version 2.0",
        description="Asynchronous pure python gRPC server and client implementation using curio "
                    "and hyper-h2.",
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
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: POSIX :: Linux",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Internet",
            "Topic :: Software Development :: Libraries",
            "Topic :: System :: Networking",
        ],
        keywords=[
            "async", "await", "grpc", "pure-python", "pypy", "network",
            "rpc", "http2",
        ],
        packages=find_packages('src'),
        package_dir={'': 'src'},
        test_suite="tests",
        python_requires=">=3.5",
        install_requires=[
            "h2>=3.1.0,<4",
            "protobuf~=3.6",
            "anyio>=1.0.0b1,<2",
            "async_exit_stack>=1.0.1,<2",
            "tblib>=1.3.2,<2",
            "async_generator>=1.10,<2.0"
        ],
        entry_points={'console_scripts': console_scripts},
        setup_requires=["pytest-runner"],
        tests_require=[
            "pytest",
            "pytest-xdist",
            "pytest-forked",
            "grpcio_tools",
            "grpcio"
        ]
    )


if __name__ == "__main__":
    main()
