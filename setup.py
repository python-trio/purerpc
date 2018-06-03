import faulthandler
faulthandler.enable()
from setuptools import setup, find_packages


def main():
    console_scripts = ['protoc-gen-purerpc=purerpc.protoc_plugin.plugin:main']
    setup(
        name="purerpc",
        version="0.0.1",
        author="Andrew Stepanov",
        description="Asynchronous pure python gRPC server and client implementation using curio "
                    "and hyper-h2.",
        packages=find_packages('src'),
        package_dir={'': 'src'},
        test_suite="tests",
        python_requires=">=3.6.0",
        install_requires=[
            "autopep8",
            "grpcio_tools",
            "objgraph",
            "h2",
            "protobuf",
            "curio~=0.9.0",
        ],
        entry_points={'console_scripts': console_scripts},
        tests_require=[
            "grpcio"
        ]
    )


if __name__ == "__main__":
    main()
