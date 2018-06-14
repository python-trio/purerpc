from setuptools import setup, find_packages


def main():
    console_scripts = ['protoc-gen-purerpc=purerpc.protoc_plugin.plugin:main']
    setup(
        name="purerpc",
        version="0.1.0",
        author="Andrew Stepanov",
        description="Asynchronous pure python gRPC server and client implementation using curio "
                    "and hyper-h2.",
        packages=find_packages('src'),
        package_dir={'': 'src'},
        test_suite="tests",
        python_requires=">=3.6.0",
        install_requires=[
            "autopep8",
            "h2",
            "protobuf",
            "curio",
        ],
        entry_points={'console_scripts': console_scripts},
        setup_requires=["pytest-runner"],
        tests_require=[
            "pytest",
            "grpcio_tools",
            "grpcio"
        ]
    )


if __name__ == "__main__":
    main()
