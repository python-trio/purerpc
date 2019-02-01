import unittest
import anyio
import grpc
import pickle
import base64
import typing
import time
from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server
from purerpc.test_utils import PureRPCTestCase

import purerpc


class TestClientServerMetadata(PureRPCTestCase):
    def test_metadata_purerpc_server_grpc_client(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer

            class Servicer(GreeterServicer):
                async def SayHello(self, message, request):
                    print("Server received metadata", request.custom_metadata)
                    return HelloReply(message=base64.b64encode(pickle.dumps(
                        request.custom_metadata)))

            with self.run_purerpc_service_in_process(Servicer().service) as port:
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
                    self.assertEqual(received_metadata[-1][0], "accept-encoding")
                    received_metadata = received_metadata[:-1]
                    self.assertEqual(metadata, received_metadata)

    def test_metadata_grpc_server_purerpc_client(self):
        class Servicer(GreeterServicer):
            def SayHello(self, message, context):
                metadata = []
                for key, value in context.invocation_metadata():
                    metadata.append((key, value))
                metadata = tuple(metadata)
                print("Server received metadata", metadata)
                return HelloReply(message=base64.b64encode(pickle.dumps(metadata)))


        with self.run_grpc_service_in_process(
                        lambda server: add_GreeterServicer_to_server(Servicer(), server)) as port, \
            self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            metadata = (
                ("name", "World"),
                ("name", "World2"),
                ("name-bin", b"1234"),
                ("name-bin", b"123"),
                ("true-bin", b"\x00\x00")
            )

            GreeterStub = grpc_module.GreeterStub
            async def worker(channel):
                stub = GreeterStub(channel)
                response = await stub.SayHello(HelloRequest(name="World"), metadata=metadata)
                received_metadata = pickle.loads(base64.b64decode(response.message))
                print("Server received metadata (in client)", received_metadata)
                self.assertEqual(received_metadata[0][0], "grpc-message-type")
                received_metadata = received_metadata[1:]
                self.assertEqual(metadata, received_metadata)


            async def main():
                async with purerpc.insecure_channel("localhost", port) as channel:
                    await worker(channel)
            anyio.run(main)

    def test_metadata_purerpc_server_purerpc_client(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer
            GreeterStub = grpc_module.GreeterStub

            class Servicer(GreeterServicer):
                async def SayHello(self, message, request):
                    print("Server received metadata", request.custom_metadata)
                    return HelloReply(message=base64.b64encode(pickle.dumps(
                        request.custom_metadata)))

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                metadata = (
                    ("name", "World"),
                    ("name", "World2"),
                    ("name-bin", b"1234"),
                    ("name-bin", b"123"),
                    ("true-bin", b"\x00\x00")
                )

                GreeterStub = grpc_module.GreeterStub

                async def worker(channel):
                    stub = GreeterStub(channel)
                    response = await stub.SayHello(HelloRequest(name="World"), metadata=metadata)
                    received_metadata = pickle.loads(base64.b64decode(response.message))
                    print("Server received metadata (in client)", received_metadata)
                    self.assertEqual(metadata, received_metadata)

                async def main():
                    async with purerpc.insecure_channel("localhost", port) as channel:
                        await worker(channel)

                anyio.run(main)
