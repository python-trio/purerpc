import time
import functools

import anyio
import grpc
import pytest
from async_generator import async_generator, yield_

from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server
from purerpc.test_utils import run_purerpc_service_in_process, run_grpc_service_in_process, run_tests_in_workers, \
    async_iterable_to_list, random_payload
import purerpc


def test_purerpc_server_grpc_client(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer

    class Servicer(GreeterServicer):
        async def SayHello(self, message):
            return HelloReply(message="Hello, " + message.name)

        @async_generator
        async def SayHelloGoodbye(self, message):
            await yield_(HelloReply(message="Hello, " + message.name))
            await anyio.sleep(0.05)
            await yield_(HelloReply(message="Goodbye, " + message.name))

        async def SayHelloToManyAtOnce(self, messages):
            names = []
            async for message in messages:
                names.append(message.name)
            return HelloReply(message="Hello, " + ', '.join(names))

        @async_generator
        async def SayHelloToMany(self, messages):
            async for message in messages:
                await anyio.sleep(0.05)
                await yield_(HelloReply(message="Hello, " + message.name))

    with run_purerpc_service_in_process(Servicer().service) as port:
        def name_generator():
            names = ('Foo', 'Bar', 'Bat', 'Baz')
            for name in names:
                yield HelloRequest(name=name)

        def target_fn():
            with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                stub = GreeterStub(channel)
                assert stub.SayHello(HelloRequest(name="World")).message == "Hello, World"
                assert [response.message for response in
                        stub.SayHelloGoodbye(HelloRequest(name="World"))] == ["Hello, World", "Goodbye, World"]
                assert stub.SayHelloToManyAtOnce(name_generator()).message == "Hello, Foo, Bar, Bat, Baz"
                assert [response.message for response in stub.SayHelloToMany(name_generator())] == \
                       ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]

        run_tests_in_workers(target=target_fn, num_workers=50)


def test_grpc_server_purerpc_client(greeter_grpc):
    class Servicer(GreeterServicer):
        def SayHello(self, message, context):
            return HelloReply(message="Hello, " + message.name)

        def SayHelloGoodbye(self, message, context):
            yield HelloReply(message="Hello, " + message.name)
            time.sleep(0.05)
            yield HelloReply(message="Goodbye, " + message.name)

        def SayHelloToMany(self, messages, context):
            for message in messages:
                time.sleep(0.05)
                yield HelloReply(message="Hello, " + message.name)

        def SayHelloToManyAtOnce(self, messages, context):
            names = []
            for message in messages:
                names.append(message.name)
            return HelloReply(message="Hello, " + ', '.join(names))

    with run_grpc_service_in_process(functools.partial(add_GreeterServicer_to_server, Servicer())) as port:
        @async_generator
        async def name_generator():
            names = ('Foo', 'Bar', 'Bat', 'Baz')
            for name in names:
                await yield_(HelloRequest(name=name))

        GreeterStub = greeter_grpc.GreeterStub
        async def worker(channel):
            stub = GreeterStub(channel)
            assert (await stub.SayHello(HelloRequest(name="World"))).message == "Hello, World"
            assert [response.message for response in await async_iterable_to_list(
                    stub.SayHelloGoodbye(HelloRequest(name="World")))] == ["Hello, World", "Goodbye, World"]
            assert (await stub.SayHelloToManyAtOnce(name_generator())).message == "Hello, Foo, Bar, Bat, Baz"
            assert [response.message for response in await async_iterable_to_list(
                    stub.SayHelloToMany(name_generator()))] == \
                   ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                async with anyio.create_task_group() as task_group:
                    for _ in range(50):
                        await task_group.spawn(worker, channel)
        anyio.run(main)


def test_purerpc_server_purerpc_client(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer
    GreeterStub = greeter_grpc.GreeterStub

    class Servicer(GreeterServicer):
        async def SayHello(self, message):
            return HelloReply(message="Hello, " + message.name)

        @async_generator
        async def SayHelloGoodbye(self, message):
            await yield_(HelloReply(message="Hello, " + message.name))
            await anyio.sleep(0.05)
            await yield_(HelloReply(message="Goodbye, " + message.name))

        async def SayHelloToManyAtOnce(self, messages):
            names = []
            async for message in messages:
                names.append(message.name)
            return HelloReply(message="Hello, " + ', '.join(names))

        @async_generator
        async def SayHelloToMany(self, messages):
            async for message in messages:
                await anyio.sleep(0.05)
                await yield_(HelloReply(message="Hello, " + message.name))

    with run_purerpc_service_in_process(Servicer().service) as port:
        @async_generator
        async def name_generator():
            names = ('Foo', 'Bar', 'Bat', 'Baz')
            for name in names:
                await yield_(HelloRequest(name=name))

        async def worker(channel):
            stub = GreeterStub(channel)
            assert (await stub.SayHello(HelloRequest(name="World"))).message == "Hello, World"
            assert [response.message for response in await async_iterable_to_list(
                    stub.SayHelloGoodbye(HelloRequest(name="World")))] == ["Hello, World", "Goodbye, World"]
            assert (await stub.SayHelloToManyAtOnce(name_generator())).message == "Hello, Foo, Bar, Bat, Baz"
            assert [response.message for response in await async_iterable_to_list(
                    stub.SayHelloToMany(name_generator()))] == \
                   ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                async with anyio.create_task_group() as task_group:
                    for _ in range(50):
                        await task_group.spawn(worker, channel)

        anyio.run(main)


def test_purerpc_server_purerpc_client_large_payload_many_streams(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer
    GreeterStub = greeter_grpc.GreeterStub

    class Servicer(GreeterServicer):
        async def SayHello(self, message):
            return HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(Servicer().service) as port:
        async def worker(channel):
            stub = GreeterStub(channel)
            data = "World" * 20000
            assert (await stub.SayHello(HelloRequest(name=data))).message == "Hello, " + data

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                async with anyio.create_task_group() as task_group:
                    for _ in range(50):
                        await task_group.spawn(worker, channel)

        anyio.run(main)


def test_purerpc_server_purerpc_client_large_payload_one_stream(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer
    GreeterStub = greeter_grpc.GreeterStub

    class Servicer(GreeterServicer):
        async def SayHello(self, message):
            return HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(Servicer().service) as port:
        async def worker(channel):
            stub = GreeterStub(channel)
            data = "World" * 20000
            assert (await stub.SayHello(HelloRequest(name=data))).message == "Hello, " + data

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                async with anyio.create_task_group() as task_group:
                    for _ in range(1):
                        await task_group.spawn(worker, channel)

        anyio.run(main)


def test_purerpc_server_grpc_client_large_payload(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer

    class Servicer(GreeterServicer):
        async def SayHello(self, message):
            return HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(Servicer().service) as port:
        def target_fn():
            with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                stub = GreeterStub(channel)
                data = "World" * 20000
                assert stub.SayHello(HelloRequest(name=data)).message == "Hello, " + data
        run_tests_in_workers(target=target_fn, num_workers=50)


def test_purerpc_server_purerpc_client_random(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer
    GreeterStub = greeter_grpc.GreeterStub

    class Servicer(GreeterServicer):
        async def SayHello(self, message):
            return HelloReply(message=message.name)

        @async_generator
        async def SayHelloGoodbye(self, message):
            await yield_(HelloReply(message=message.name))
            await yield_(HelloReply(message=message.name))

        async def SayHelloToManyAtOnce(self, messages):
            names = []
            async for message in messages:
                names.append(message.name)
            return HelloReply(message="".join(names))

        @async_generator
        async def SayHelloToMany(self, messages):
            async for message in messages:
                await yield_(HelloReply(message=message.name))

    with run_purerpc_service_in_process(Servicer().service) as port:
        async def worker(channel):
            stub = GreeterStub(channel)
            data = random_payload()

            @async_generator
            async def gen():
                for _ in range(4):
                    await yield_(HelloRequest(name=data))
            assert (await stub.SayHello(HelloRequest(name=data))).message == data
            assert [response.message for response in await async_iterable_to_list(
                    stub.SayHelloGoodbye(HelloRequest(name=data)))] == [data] * 2
            assert (await stub.SayHelloToManyAtOnce(gen())).message == data * 4
            assert [response.message for response in await async_iterable_to_list(
                    stub.SayHelloToMany(gen()))] == [data] * 4

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                async with anyio.create_task_group() as task_group:
                    for _ in range(20):
                        await task_group.spawn(worker, channel)

        anyio.run(main)


def test_purerpc_server_purerpc_client_deadlock(greeter_grpc):
    GreeterServicer = greeter_grpc.GreeterServicer
    GreeterStub = greeter_grpc.GreeterStub

    class Servicer(GreeterServicer):
        @async_generator
        async def SayHelloToMany(self, messages):
            data = ""
            async for message in messages:
                data += message.name
            await yield_(HelloReply(message=data))

    with run_purerpc_service_in_process(Servicer().service) as port:
        async def worker(channel):
            stub = GreeterStub(channel)
            data = random_payload(min_size=32000, max_size=64000)

            @async_generator
            async def gen():
                for _ in range(20):
                    await yield_(HelloRequest(name=data))
            assert [response.message for response in await async_iterable_to_list(
                    stub.SayHelloToMany(gen()))] == [data * 20]

        async def main():
            async with purerpc.insecure_channel("localhost", port) as channel:
                async with anyio.create_task_group() as task_group:
                    for _ in range(10):
                        await task_group.spawn(worker, channel)

        anyio.run(main)
