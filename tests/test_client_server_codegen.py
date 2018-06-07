import unittest
import curio
import grpc
import typing
import time
from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server
from purerpc import Service, Stream, Channel, Client
from .test_case_base import PureRPCTestCase


class TestClientServerCodegen(PureRPCTestCase):
    def test_purerpc_server_grpc_client(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = getattr(grpc_module, "GreeterServicer")

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    return HelloReply(message=f"Hello, {message.name}")

                async def SayHelloGoodbye(self, message):
                    yield HelloReply(message=f"Hello, {message.name}")
                    await curio.sleep(0.05)
                    yield HelloReply(message=f"Goodbye, {message.name}")

                async def SayHelloToManyAtOnce(self, messages):
                    names = []
                    async for message in messages:
                        names.append(message.name)
                    return HelloReply(message=f"Hello, {', '.join(names)}")

                async def SayHelloToMany(self, messages):
                    async for message in messages:
                        await curio.sleep(0.05)
                        yield HelloReply(message="Hello, " + message.name)

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                def name_generator():
                    names = ('Foo', 'Bar', 'Bat', 'Baz')
                    for name in names:
                        yield HelloRequest(name=name)

                with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                    stub = GreeterStub(channel)
                    self.assertEqual(
                        stub.SayHello(HelloRequest(name="World")).message,
                        "Hello, World"
                    )
                    self.assertEqual(
                        [response.message for response in
                            stub.SayHelloGoodbye(HelloRequest(name="World"))],
                        ["Hello, World", "Goodbye, World"]
                    )
                    self.assertEqual(
                        stub.SayHelloToManyAtOnce(name_generator()).message,
                        "Hello, Foo, Bar, Bat, Baz"
                    )
                    self.assertEqual(
                        [response.message for response in stub.SayHelloToMany(name_generator())],
                        ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]
                    )

    def test_grpc_server_purerpc_client(self):
        class Servicer(GreeterServicer):
            def SayHello(self, message, context):
                return HelloReply(message=f"Hello, {message.name}")

            def SayHelloGoodbye(self, message, context):
                yield HelloReply(message=f"Hello, {message.name}")
                time.sleep(0.05)
                yield HelloReply(message=f"Goodbye, {message.name}")

            def SayHelloToMany(self, messages, context):
                for message in messages:
                    time.sleep(0.05)
                    yield HelloReply(message="Hello, " + message.name)

            def SayHelloToManyAtOnce(self, messages, context):
                names = []
                for message in messages:
                    names.append(message.name)
                return HelloReply(message=f"Hello, {', '.join(names)}")

        with self.run_grpc_service_in_process(
                        lambda server: add_GreeterServicer_to_server(Servicer(), server)) as port, \
             self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):

            async def name_generator():
                names = ('Foo', 'Bar', 'Bat', 'Baz')
                for name in names:
                    yield HelloRequest(name=name)
            
            GreeterStub = getattr(grpc_module, "GreeterStub")
            async def worker(channel):
                stub = GreeterStub(channel)
                self.assertEqual(
                    (await stub.SayHello(HelloRequest(name="World"))).message,
                    "Hello, World"
                )
                self.assertEqual(
                    [response.message async for response in
                        stub.SayHelloGoodbye(HelloRequest(name="World"))],
                    ["Hello, World", "Goodbye, World"]
                )
                self.assertEqual(
                    (await stub.SayHelloToManyAtOnce(name_generator())).message,
                    "Hello, Foo, Bar, Bat, Baz"
                )
                self.assertEqual(
                    [response.message async for response in stub.SayHelloToMany(name_generator())],
                    ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]
                )

            async def main():
                channel = Channel("localhost", port)
                await channel.connect()
                async with curio.TaskGroup() as task_group:
                    for _ in range(5):
                        await task_group.spawn(worker(channel))
            curio.run(main)

    def test_purerpc_server_purerpc_client(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = getattr(grpc_module, "GreeterServicer")
            GreeterStub = getattr(grpc_module, "GreeterStub")

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    return HelloReply(message=f"Hello, {message.name}")

                async def SayHelloGoodbye(self, message):
                    yield HelloReply(message=f"Hello, {message.name}")
                    await curio.sleep(0.05)
                    yield HelloReply(message=f"Goodbye, {message.name}")

                async def SayHelloToManyAtOnce(self, messages):
                    names = []
                    async for message in messages:
                        names.append(message.name)
                    return HelloReply(message=f"Hello, {', '.join(names)}")

                async def SayHelloToMany(self, messages):
                    async for message in messages:
                        await curio.sleep(0.05)
                        yield HelloReply(message="Hello, " + message.name)

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                async def name_generator():
                    names = ('Foo', 'Bar', 'Bat', 'Baz')
                    for name in names:
                        yield HelloRequest(name=name)

                async def worker(channel):
                    stub = GreeterStub(channel)
                    self.assertEqual(
                        (await stub.SayHello(HelloRequest(name="World"))).message,
                        "Hello, World"
                    )
                    self.assertEqual(
                        [response.message async for response in
                            stub.SayHelloGoodbye(HelloRequest(name="World"))],
                        ["Hello, World", "Goodbye, World"]
                    )
                    self.assertEqual(
                        (await stub.SayHelloToManyAtOnce(name_generator())).message,
                        "Hello, Foo, Bar, Bat, Baz"
                    )
                    self.assertEqual(
                        [response.message async for response in stub.SayHelloToMany(name_generator())],
                        ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]
                    )

                async def main():
                    channel = Channel("localhost", port)
                    await channel.connect()
                    async with curio.TaskGroup() as task_group:
                        for _ in range(5):
                            await task_group.spawn(worker(channel))

                curio.run(main)
