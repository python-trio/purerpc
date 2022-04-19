import functools
import pickle
import base64

import pytest

from purerpc.test_utils import (run_purerpc_service_in_process, run_grpc_service_in_process, grpc_client_parallelize,
                                grpc_channel, purerpc_channel)

pytestmark = pytest.mark.anyio


METADATA = (
    ("name", "World"),
    ("name", "World2"),
    ("name-bin", b"1234"),
    ("name-bin", b"123"),
    ("true-bin", b"\x00\x00")
)


@pytest.fixture(scope="module")
def purerpc_port(greeter_pb2, greeter_grpc):
    class Servicer(greeter_grpc.GreeterServicer):
        async def SayHello(self, message, request):
            return greeter_pb2.HelloReply(message=base64.b64encode(pickle.dumps(
                request.custom_metadata)))

    with run_purerpc_service_in_process(Servicer().service) as port:
        yield port


@pytest.fixture(scope="module")
def grpc_port(greeter_pb2, greeter_pb2_grpc):
    class Servicer(greeter_pb2_grpc.GreeterServicer):
        def SayHello(self, message, context):
            metadata = []
            for key, value in context.invocation_metadata():
                metadata.append((key, value))
            metadata = tuple(metadata)
            return greeter_pb2.HelloReply(message=base64.b64encode(pickle.dumps(metadata)))

    with run_grpc_service_in_process(functools.partial(
            greeter_pb2_grpc.add_GreeterServicer_to_server, Servicer())) as port:
        yield port


@grpc_client_parallelize(1)
@grpc_channel("purerpc_port")
def test_metadata_grpc_client(greeter_pb2, greeter_pb2_grpc, channel):
    stub = greeter_pb2_grpc.GreeterStub(channel)
    response = stub.SayHello(greeter_pb2.HelloRequest(name="World"), metadata=METADATA)

    received_metadata = pickle.loads(base64.b64decode(response.message))
    # remove artifact of older grpcio versions
    if received_metadata[-1][0] == "accept-encoding":
        received_metadata = received_metadata[:-1]
    assert METADATA == received_metadata


@purerpc_channel("grpc_port")
async def test_metadata_grpc_server_purerpc_client(greeter_pb2, greeter_grpc, channel):
    stub = greeter_grpc.GreeterStub(channel)
    response = await stub.SayHello(greeter_pb2.HelloRequest(name="World"), metadata=METADATA)

    received_metadata = pickle.loads(base64.b64decode(response.message))
    assert received_metadata[0][0] == "grpc-message-type"
    received_metadata = received_metadata[1:]
    assert METADATA == received_metadata


@purerpc_channel("purerpc_port")
async def test_metadata_purerpc_server_purerpc_client(greeter_pb2, greeter_grpc, channel):
    stub = greeter_grpc.GreeterStub(channel)
    response = await stub.SayHello(greeter_pb2.HelloRequest(name="World"), metadata=METADATA)

    received_metadata = pickle.loads(base64.b64decode(response.message))
    assert METADATA == received_metadata
