import functools
import pickle
import base64


import anyio
import grpc

from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server
from purerpc.test_utils import run_purerpc_service_in_process, run_grpc_service_in_process

import purerpc


def test_metadata_purerpc_server_grpc_client(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer

    class Servicer(GreeterServicer):
        async def SayHello(self, message, request):
            print("Server received metadata", request.custom_metadata)
            return HelloReply(message=base64.b64encode(pickle.dumps(
                request.custom_metadata)))

    with run_purerpc_service_in_process(Servicer().service) as port:
        with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
            stub = GreeterStub(channel)
            metadata = (
                ("name", "World"),
                ("name", "World2"),
                ("name-bin", b"1234"),
                ("name-bin", b"123"),
                ("true-bin", b"\x00\x00")
            )
            response = stub.SayHello(HelloRequest(name="World"),
                          metadata=metadata)
            received_metadata = pickle.loads(base64.b64decode(response.message))
            print("Server received metadata (in client)", received_metadata)
            assert received_metadata[-1][0] == "accept-encoding"
            received_metadata = received_metadata[:-1]
            assert metadata == received_metadata


def test_metadata_grpc_server_purerpc_client(greeter_grpc):
    class Servicer(GreeterServicer):
        def SayHello(self, message, context):
            metadata = []
            for key, value in context.invocation_metadata():
                metadata.append((key, value))
            metadata = tuple(metadata)
            print("Server received metadata", metadata)
            return HelloReply(message=base64.b64encode(pickle.dumps(metadata)))


    with run_grpc_service_in_process(functools.partial(add_GreeterServicer_to_server, Servicer())) as port:
        metadata = (
            ("name", "World"),
            ("name", "World2"),
            ("name-bin", b"1234"),
            ("name-bin", b"123"),
            ("true-bin", b"\x00\x00")
        )

        GreeterStub = greeter_grpc.GreeterStub
        async def worker(channel):
            stub = GreeterStub(channel)
            response = await stub.SayHello(HelloRequest(name="World"), metadata=metadata)
            received_metadata = pickle.loads(base64.b64decode(response.message))
            print("Server received metadata (in client)", received_metadata)
            assert received_metadata[0][0] == "grpc-message-type"
            received_metadata = received_metadata[1:]
            assert metadata == received_metadata


        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                await worker(channel)
        anyio.run(main)


def test_metadata_purerpc_server_purerpc_client(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer
    GreeterStub = greeter_grpc.GreeterStub

    class Servicer(GreeterServicer):
        async def SayHello(self, message, request):
            print("Server received metadata", request.custom_metadata)
            return HelloReply(message=base64.b64encode(pickle.dumps(
                request.custom_metadata)))

    with run_purerpc_service_in_process(Servicer().service) as port:
        metadata = (
            ("name", "World"),
            ("name", "World2"),
            ("name-bin", b"1234"),
            ("name-bin", b"123"),
            ("true-bin", b"\x00\x00")
        )

        GreeterStub = greeter_grpc.GreeterStub

        async def worker(channel):
            stub = GreeterStub(channel)
            response = await stub.SayHello(HelloRequest(name="World"), metadata=metadata)
            received_metadata = pickle.loads(base64.b64decode(response.message))
            print("Server received metadata (in client)", received_metadata)
            assert metadata == received_metadata

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                await worker(channel)

        anyio.run(main)
