import pytest

from purerpc.test_utils import compile_temp_proto


@pytest.fixture(scope="session")
def greeter_modules():
    with compile_temp_proto("data/greeter.proto", add_pb2_grpc_module=True) as modules:
        yield modules


@pytest.fixture(scope="session")
def greeter_pb2(greeter_modules):
    return greeter_modules[0]


@pytest.fixture(scope="session")
def greeter_pb2_grpc(greeter_modules):
    return greeter_modules[1]


@pytest.fixture(scope="session")
def greeter_grpc(greeter_modules):
    return greeter_modules[2]


@pytest.fixture(scope="session")
def echo_modules():
    with compile_temp_proto("data/echo.proto", add_pb2_grpc_module=True) as modules:
        yield modules


@pytest.fixture(scope="session")
def echo_pb2(echo_modules):
    return echo_modules[0]


@pytest.fixture(scope="session")
def echo_pb2_grpc(echo_modules):
    return echo_modules[1]


@pytest.fixture(scope="session")
def echo_grpc(echo_modules):
    return echo_modules[2]
