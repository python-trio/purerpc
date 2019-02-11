import functools

import anyio
import grpc
import pytest

from async_generator import async_generator, aclosing, yield_

from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server

import purerpc
from purerpc.test_utils import run_purerpc_service_in_process, run_grpc_service_in_process


def test_errors_purerpc_server_grpc_client(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer

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

    with run_purerpc_service_in_process(Servicer().service) as port:
        with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
            stub = GreeterStub(channel)
            with pytest.raises(grpc._channel._Rendezvous, match=r"oops my bad"):
                stub.SayHello(HelloRequest(name="World"))

            with pytest.raises(grpc._channel._Rendezvous, match=r"Lucky 7"):
                for _ in stub.SayHelloToMany(HelloRequest() for _ in range(10)):
                    pass


def test_errors_grpc_server_purerpc_client(greeter_grpc):
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

    with run_grpc_service_in_process(functools.partial(add_GreeterServicer_to_server, Servicer())) as port:

        @async_generator
        async def generator():
            for _ in range(7):
                await yield_(HelloRequest())

        GreeterStub = greeter_grpc.GreeterStub
        async def worker(channel):
            stub = GreeterStub(channel)
            with pytest.raises(purerpc.RpcFailedError, match=r"oops my bad"):
                await stub.SayHello(HelloRequest(name="World"))

            async with aclosing(stub.SayHelloToMany(generator())) as aiter:
                for _ in range(7):
                    await aiter.__anext__()
                with pytest.raises(purerpc.RpcFailedError, match=r"Lucky 7"):
                    await aiter.__anext__()

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                await worker(channel)
        anyio.run(main)


def test_errors_purerpc_server_purerpc_client(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer
    GreeterStub = greeter_grpc.GreeterStub

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

    with run_purerpc_service_in_process(Servicer().service) as port:
        @async_generator
        async def generator():
            for _ in range(10):
                await yield_(HelloRequest())

        async def worker(channel):
            stub = GreeterStub(channel)
            with pytest.raises(purerpc.RpcFailedError, match="oops my bad"):
                await stub.SayHello(HelloRequest(name="World"))

            aiter = stub.SayHelloToMany(generator())
            for _ in range(7):
                await aiter.__anext__()
            with pytest.raises(purerpc.RpcFailedError, match=r"Lucky 7"):
                await aiter.__anext__()

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                await worker(channel)

        anyio.run(main)
