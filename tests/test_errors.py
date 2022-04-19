import functools

import pytest

from async_generator import aclosing

import purerpc
from purerpc.test_utils import run_purerpc_service_in_process, run_grpc_service_in_process, grpc_channel, \
    grpc_client_parallelize, purerpc_channel

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="module")
def purerpc_port(greeter_pb2, greeter_grpc):
    class Servicer(greeter_grpc.GreeterServicer):
        async def SayHello(self, message):
            raise ValueError("oops my bad")

        async def SayHelloToMany(self, messages):
            idx = 1
            async for _ in messages:
                yield greeter_pb2.HelloReply(message=str(idx))
                if idx == 7:
                    raise ValueError("Lucky 7")
                idx += 1
    with run_purerpc_service_in_process(Servicer().service) as port:
        yield port


@pytest.fixture(scope="module")
def grpc_port(greeter_pb2, greeter_pb2_grpc):
    class Servicer(greeter_pb2_grpc.GreeterServicer):
        def SayHello(self, message, context):
            raise ValueError("oops my bad")

        def SayHelloToMany(self, messages, context):
            idx = 1
            for _ in messages:
                yield greeter_pb2.HelloReply(message=str(idx))
                if idx == 7:
                    raise ValueError("Lucky 7")
                idx += 1

    with run_grpc_service_in_process(functools.partial(
            greeter_pb2_grpc.add_GreeterServicer_to_server, Servicer())) as port:
        yield port


@pytest.fixture(scope="module",
                params=["purerpc_port", "grpc_port"])
def port(request):
    return request.getfixturevalue(request.param)


@grpc_client_parallelize(1)
@grpc_channel("purerpc_port")
def test_errors_grpc_client(greeter_pb2, greeter_pb2_grpc, channel):
    stub = greeter_pb2_grpc.GreeterStub(channel)
    with pytest.raises(BaseException, match=r"oops my bad"):
        stub.SayHello(greeter_pb2.HelloRequest(name="World"))

    with pytest.raises(BaseException, match=r"Lucky 7"):
        for _ in stub.SayHelloToMany(greeter_pb2.HelloRequest() for _ in range(10)):
            pass


@purerpc_channel("port")
async def test_errors_purerpc_client(greeter_pb2, greeter_grpc, channel):
    async def generator():
        for _ in range(7):
            yield greeter_pb2.HelloRequest()

    stub = greeter_grpc.GreeterStub(channel)
    with pytest.raises(purerpc.RpcFailedError, match=r"oops my bad"):
        await stub.SayHello(greeter_pb2.HelloRequest(name="World"))

    async with aclosing(stub.SayHelloToMany(generator())) as aiter:
        for _ in range(7):
            await aiter.__anext__()
        with pytest.raises(purerpc.RpcFailedError, match=r"Lucky 7"):
            await aiter.__anext__()
