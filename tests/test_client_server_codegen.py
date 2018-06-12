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
            GreeterServicer = grpc_module.GreeterServicer

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

                def target_fn():
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
                            [response.message for response
                                in stub.SayHelloToMany(name_generator())],
                            ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]
                        )

                self.run_tests_in_workers(target=target_fn, num_workers=50)

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
            
            GreeterStub = grpc_module.GreeterStub
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
                    for _ in range(50):
                        await task_group.spawn(worker(channel))
            curio.run(main)

    def test_purerpc_server_purerpc_client(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer
            GreeterStub = grpc_module.GreeterStub

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
                        for _ in range(50):
                            await task_group.spawn(worker(channel))

                curio.run(main)

    def test_purerpc_server_purerpc_client_large_payload_many_streams(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer
            GreeterStub = grpc_module.GreeterStub

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    return HelloReply(message=f"Hello, {message.name}")

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                async def worker(channel):
                    stub = GreeterStub(channel)
                    data = "World" * 20000
                    self.assertEqual(
                        (await stub.SayHello(HelloRequest(name=data))).message,
                        "Hello, " + data
                    )

                async def main():
                    channel = Channel("localhost", port)
                    await channel.connect()
                    async with curio.TaskGroup() as task_group:
                        for _ in range(50):
                            await task_group.spawn(worker(channel))

                curio.run(main)

    def test_purerpc_server_purerpc_client_large_payload_one_stream(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer
            GreeterStub = grpc_module.GreeterStub

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    return HelloReply(message=f"Hello, {message.name}")

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                async def worker(channel):
                    stub = GreeterStub(channel)
                    data = "World" * 20000
                    self.assertEqual(
                        (await stub.SayHello(HelloRequest(name=data))).message,
                        "Hello, " + data
                    )

                async def main():
                    channel = Channel("localhost", port)
                    await channel.connect()
                    async with curio.TaskGroup() as task_group:
                        for _ in range(1):
                            await task_group.spawn(worker(channel))

                curio.run(main)

    def test_purerpc_server_grpc_client_large_payload(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    return HelloReply(message=f"Hello, {message.name}")

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                def target_fn():
                    with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                        stub = GreeterStub(channel)
                        data = "World" * 20000
                        self.assertEqual(
                            stub.SayHello(HelloRequest(name=data)).message,
                            "Hello, " + data
                        )
                self.run_tests_in_workers(target=target_fn, num_workers=50)

    def test_purerpc_server_purerpc_client_random(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer
            GreeterStub = grpc_module.GreeterStub

            class Servicer(GreeterServicer):
                async def SayHello(self, message):
                    return HelloReply(message=message.name)

                async def SayHelloGoodbye(self, message):
                    yield HelloReply(message=message.name)
                    yield HelloReply(message=message.name)

                async def SayHelloToManyAtOnce(self, messages):
                    names = []
                    async for message in messages:
                        names.append(message.name)
                    return HelloReply(message="".join(names))

                async def SayHelloToMany(self, messages):
                    async for message in messages:
                        yield HelloReply(message=message.name)

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                async def worker(channel):
                    stub = GreeterStub(channel)
                    data = self.random_payload()
                    async def gen():
                        for _ in range(4):
                            yield HelloRequest(name=data)
                    self.assertEqual(
                        (await stub.SayHello(HelloRequest(name=data))).message,
                        data
                    )
                    self.assertEqual(
                        [response.message async for response in
                            stub.SayHelloGoodbye(HelloRequest(name=data))],
                        [data, data]
                    )
                    self.assertEqual(
                        (await stub.SayHelloToManyAtOnce(gen())).message,
                        data + data + data + data
                    )
                    self.assertEqual(
                        [response.message async for response in stub.SayHelloToMany(gen())],
                        [data, data, data, data]
                    )

                async def main():
                    channel = Channel("localhost", port)
                    await channel.connect()
                    async with curio.TaskGroup() as task_group:
                        for _ in range(20):
                            await task_group.spawn(worker(channel))

                curio.run(main)


    def test_purerpc_server_purerpc_client_deadlock(self):
        with self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            GreeterServicer = grpc_module.GreeterServicer
            GreeterStub = grpc_module.GreeterStub

            class Servicer(GreeterServicer):
                async def SayHelloToMany(self, messages):
                    data = ""
                    async for message in messages:
                        data += message.name
                    yield HelloReply(message=data)

            with self.run_purerpc_service_in_process(Servicer().service) as port:
                async def worker(channel):
                    stub = GreeterStub(channel)
                    data = self.random_payload(min_size=32000, max_size=64000)
                    async def gen():
                        for _ in range(20):
                            yield HelloRequest(name=data)
                    self.assertEqual(
                        [response.message async for response in stub.SayHelloToMany(gen())],
                        [data * 20]
                    )

                async def main():
                    channel = Channel("localhost", port)
                    await channel.connect()
                    async with curio.TaskGroup() as task_group:
                        for _ in range(1):
                            await task_group.spawn(worker(channel))

                curio.run(main)
