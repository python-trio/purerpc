import pytest

from purerpc.test_utils import compile_temp_proto


@pytest.fixture(scope="session")
def greeter_modules():
    with compile_temp_proto("data/greeter.proto") as modules:
        yield modules


@pytest.fixture(scope="session")
def greeter_pb2(greeter_modules):
    return greeter_modules[0]


# @pytest.fixture(scope="session")
# def greeter_pb2_grpc(greeter_modules):
#     return greeter_modules[1]


@pytest.fixture(scope="session")
def greeter_grpc(greeter_modules):
    return greeter_modules[1]
