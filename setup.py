from setuptools import setup, find_packages


def main():
    setup(
        name="purerpc",
        version="0.1",
        author="Andrew Stepanov",
        description="Asynchronous pure python gRPC server and client implementation using trio and "
                    "hyper-h2.",
        packages=find_packages('src'),
        package_dir={'': 'src'},
        test_suite="tests",
        python_requires=">=3.5.2",
        install_requires=[
            "async_generator",
            "h2",
            "protobuf",
            "curio~=0.9.0",
        ],
        tests_require=[
            "grpcio"
        ]
    )


if __name__ == "__main__":
    main()
