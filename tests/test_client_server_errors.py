import unittest
import anyio
import grpc
import typing
import time

from async_generator import async_generator, yield_

from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server

import purerpc
from purerpc.test_utils import PureRPCTestCase


class TestClientServerErrors(PureRPCTestCase):
    def test_errors_purerpc_server_grpc_client(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    raise ValueError("oops my bad")

                @async_generator
                async def SayHelloToMany(self, messages):
                    idx = 1
                    async for _ in messages:
                        await yield_(HelloReply(message=str(idx)))
                        if idx == 7:
                            raise ValueError("Lucky 7")
                        idx += 1

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                    stub = GreeterStub(channel)
                    with self.assertRaisesRegex(grpc._channel._Rendezvous, r"oops my bad"):
                        stub.SayHello(HelloRequest(name="World"))

                    with self.assertRaisesRegex(grpc._channel._Rendezvous, r"Lucky 7"):
                        for _ in stub.SayHelloToMany(HelloRequest() for _ in range(10)):
                            pass

    def test_errors_grpc_server_purerpc_client(self):
        class Servicer(GreeterServicer):
            def SayHello(self, message, context):
                raise ValueError("oops my bad")

            def SayHelloToMany(self, messages, context):
                idx = 1
                for _ in messages:
                    yield HelloReply(message=str(idx))
                    if idx == 7:
                        raise ValueError("Lucky 7")
                    idx += 1

        with self.run_grpc_service_in_process(
                        lambda server: add_GreeterServicer_to_server(Servicer(), server)) as port, \
             self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):

            @async_generator
            async def generator():
                for _ in range(10):
                    await yield_(HelloRequest())

            GreeterStub = grpc_module.GreeterStub
            async def worker(channel):
                stub = GreeterStub(channel)
                with self.assertRaisesRegex(purerpc.RpcFailedError, r"oops my bad"):
                    await stub.SayHello(HelloRequest(name="World"))

                aiter = stub.SayHelloToMany(generator())
                for _ in range(7):
                    await aiter.__anext__()
                with self.assertRaisesRegex(purerpc.RpcFailedError, r"Lucky 7"):
                    await aiter.__anext__()

            async def main():
                async with purerpc.insecure_channel("localhost", port) as channel:
                    await worker(channel)
            anyio.run(main)

    def test_errors_purerpc_server_purerpc_client(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer
            GreeterStub = grpc_module.GreeterStub

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    raise ValueError("oops my bad")

                @async_generator
                async def SayHelloToMany(self, messages):
                    idx = 1
                    async for _ in messages:
                        await yield_(HelloReply(message=str(idx)))
                        if idx == 7:
                            raise ValueError("Lucky 7")
                        idx += 1

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                @async_generator
                async def generator():
                    for _ in range(10):
                        await yield_(HelloRequest())

                async def worker(channel):
                    stub = GreeterStub(channel)
                    with self.assertRaisesRegex(purerpc.RpcFailedError, "oops my bad"):
                        await stub.SayHello(HelloRequest(name="World"))

                    aiter = stub.SayHelloToMany(generator())
                    for _ in range(7):
                        await aiter.__anext__()
                    with self.assertRaisesRegex(purerpc.RpcFailedError, r"Lucky 7"):
                        await aiter.__anext__()

                async def main():
                    async with purerpc.insecure_channel("localhost", port) as channel:
                        await worker(channel)

                anyio.run(main)
