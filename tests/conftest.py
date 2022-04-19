import platform

import pytest

from purerpc.test_utils import compile_temp_proto

pytestmark = pytest.mark.anyio


@pytest.fixture(params=[
    pytest.param(('trio'), id='trio'),
    pytest.param(('asyncio'), id='asyncio'),
    pytest.param(('asyncio', dict(use_uvloop=True)), id='uvloop',
                 marks=[pytest.mark.skipif(platform.system() == 'Windows',
                                           reason='uvloop not supported on Windows')]),
])
def anyio_backend(request):
    return request.param


@pytest.fixture(scope="session")
def greeter_modules():
    with compile_temp_proto("data/greeter.proto") as modules:
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
    with compile_temp_proto("data/echo.proto") as modules:
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
