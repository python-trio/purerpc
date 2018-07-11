import unittest
import curio
import grpc
import typing
import time
from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server
from purerpc import Service, Stream, Channel, Client
from purerpc.test_utils import PureRPCTestCase


class TestClientServerSimple(PureRPCTestCase):
    def test_purerpc_server_grpc_client(self):
        service = Service("Greeter")

        @service.rpc("SayHello")
        async def say_hello(message: HelloRequest) -> HelloReply:
            return HelloReply(message=f"Hello, {message.name}")

        @service.rpc("SayHelloGoodbye")
        async def say_hello_goodbye(message: HelloRequest) -> Stream[HelloReply]:
            yield HelloReply(message=f"Hello, {message.name}")
            await curio.sleep(0.05)
            yield HelloReply(message=f"Goodbye, {message.name}")

        @service.rpc("SayHelloToManyAtOnce")
        async def say_hello_to_many_at_once(messages: Stream[HelloRequest]) -> HelloReply:
            names = []
            async for message in messages:
                names.append(message.name)
            return HelloReply(message=f"Hello, {', '.join(names)}")

        @service.rpc("SayHelloToMany")
        async def say_hello_to_many(messages: Stream[HelloRequest]) -> Stream[HelloReply]:
            async for message in messages:
                await curio.sleep(0.05)
                yield HelloReply(message="Hello, " + message.name)

        with self.run_purerpc_service_in_process(service) as port:
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
                        [response.message for response in stub.SayHelloToMany(name_generator())],
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
                        lambda server: add_GreeterServicer_to_server(Servicer(), server)) as port:
            async def test_say_hello(client):
                stream = await client.rpc("SayHello", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="World"))
                await stream.close()
                self.assertEqual((await stream.receive_message()).message, "Hello, World")
                self.assertIsNone(await stream.receive_message())

            async def test_say_hello_goodbye(client):
                stream = await client.rpc("SayHelloGoodbye", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="World"))
                await stream.close()
                self.assertEqual((await stream.receive_message()).message, "Hello, World")
                self.assertEqual((await stream.receive_message()).message, "Goodbye, World")
                self.assertIsNone(await stream.receive_message())

            async def test_say_hello_to_many(client):
                stream = await client.rpc("SayHelloToMany", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="Foo"))
                self.assertEqual((await stream.receive_message()).message, "Hello, Foo")
                await stream.send_message(HelloRequest(name="Bar"))
                self.assertEqual((await stream.receive_message()).message, "Hello, Bar")
                await stream.send_message(HelloRequest(name="Baz"))
                await stream.send_message(HelloRequest(name="World"))
                self.assertEqual((await stream.receive_message()).message, "Hello, Baz")
                self.assertEqual((await stream.receive_message()).message, "Hello, World")
                await stream.close()
                self.assertIsNone(await stream.receive_message())

            async def test_say_hello_to_many_at_once(client):
                stream = await client.rpc("SayHelloToManyAtOnce", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="Foo"))
                await stream.send_message(HelloRequest(name="Bar"))
                await stream.send_message(HelloRequest(name="Baz"))
                await stream.send_message(HelloRequest(name="World"))
                await stream.close()
                self.assertEqual((await stream.receive_message()).message,
                                 "Hello, Foo, Bar, Baz, World")
                self.assertIsNone(await stream.receive_message())
            
            async def worker(channel):
                client = Client("Greeter", channel)
                await test_say_hello(client)
                await test_say_hello_goodbye(client)
                await test_say_hello_to_many(client)
                await test_say_hello_to_many_at_once(client)

            async def main():
                channel = Channel("localhost", port)
                await channel.connect()
                async with curio.TaskGroup() as task_group:
                    for _ in range(50):
                        await task_group.spawn(worker(channel))
            curio.run(main)

    def test_purerpc_server_purerpc_client(self):
        service = Service("Greeter")

        @service.rpc("SayHello")
        async def say_hello(message: HelloRequest) -> HelloReply:
            return HelloReply(message=f"Hello, {message.name}")

        @service.rpc("SayHelloGoodbye")
        async def say_hello_goodbye(message: HelloRequest) -> Stream[HelloReply]:
            yield HelloReply(message=f"Hello, {message.name}")
            await curio.sleep(0.05)
            yield HelloReply(message=f"Goodbye, {message.name}")

        @service.rpc("SayHelloToManyAtOnce")
        async def say_hello_to_many_at_once(messages: Stream[HelloRequest]) -> HelloReply:
            names = []
            async for message in messages:
                names.append(message.name)
            return HelloReply(message=f"Hello, {', '.join(names)}")

        @service.rpc("SayHelloToMany")
        async def say_hello_to_many(messages: Stream[HelloRequest]) -> Stream[HelloReply]:
            async for message in messages:
                await curio.sleep(0.05)
                yield HelloReply(message="Hello, " + message.name)

        with self.run_purerpc_service_in_process(service) as port:
            async def test_say_hello(client):
                stream = await client.rpc("SayHello", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="World"))
                await stream.close()
                self.assertEqual((await stream.receive_message()).message, "Hello, World")
                self.assertIsNone(await stream.receive_message())

            async def test_say_hello_goodbye(client):
                stream = await client.rpc("SayHelloGoodbye", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="World"))
                await stream.close()
                self.assertEqual((await stream.receive_message()).message, "Hello, World")
                self.assertEqual((await stream.receive_message()).message, "Goodbye, World")
                self.assertIsNone(await stream.receive_message())

            async def test_say_hello_to_many(client):
                stream = await client.rpc("SayHelloToMany", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="Foo"))
                self.assertEqual((await stream.receive_message()).message, "Hello, Foo")
                await stream.send_message(HelloRequest(name="Bar"))
                self.assertEqual((await stream.receive_message()).message, "Hello, Bar")
                await stream.send_message(HelloRequest(name="Baz"))
                await stream.send_message(HelloRequest(name="World"))
                self.assertEqual((await stream.receive_message()).message, "Hello, Baz")
                self.assertEqual((await stream.receive_message()).message, "Hello, World")
                await stream.close()
                self.assertIsNone(await stream.receive_message())

            async def test_say_hello_to_many_at_once(client):
                stream = await client.rpc("SayHelloToManyAtOnce", HelloRequest, HelloReply)
                await stream.send_message(HelloRequest(name="Foo"))
                await stream.send_message(HelloRequest(name="Bar"))
                await stream.send_message(HelloRequest(name="Baz"))
                await stream.send_message(HelloRequest(name="World"))
                await stream.close()
                self.assertEqual((await stream.receive_message()).message,
                                 "Hello, Foo, Bar, Baz, World")
                self.assertIsNone(await stream.receive_message())

            async def worker(channel):
                client = Client("Greeter", channel)
                await test_say_hello(client)
                await test_say_hello_goodbye(client)
                await test_say_hello_to_many(client)
                await test_say_hello_to_many_at_once(client)

            async def main():
                channel = Channel("localhost", port)
                await channel.connect()
                async with curio.TaskGroup() as task_group:
                    for _ in range(50):
                        await task_group.spawn(worker(channel))
            curio.run(main)
