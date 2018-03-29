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
            "trio~=0.3.0",
            "h2~=3.0.1",
            "protobuf",
        ],
        tests_require=[
            "grpcio"
        ]
    )


if __name__ == "__main__":
    main()
