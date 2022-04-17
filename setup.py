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
        description=("Native, async Python gRPC client and server implementation "
                     "supporting asyncio, uvloop, trio"),
        long_description=(
            re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.md'))
        ),
        long_description_content_type='text/markdown',
        author="Andrew Stepanov",
        url="https://github.com/python-trio/purerpc",
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
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Framework :: AsyncIO",
            "Framework :: Trio",
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
        test_suite="tests",
        python_requires=">=3.7",
        install_requires=[
            "h2>=3.1.0,<4",
            "protobuf>=3.5.1",
            "anyio>=3.0.0",
            "tblib>=1.3.2",
            "async_generator>=1.10",  # for aclosing() only (Python < 3.10)
        ],
        entry_points={
            "console_scripts": console_scripts,
        },
        extras_require={
            'test': [
                "pytest",
                "grpcio>=1.25.0",           # fix version for PyPy
                "grpcio_tools>=1.25.0",     # same here
                "uvloop",
                "trio>=0.11",
                "python-forge>=18.6",
                "trustme",
            ]
        },
    )


if __name__ == "__main__":
    main()
