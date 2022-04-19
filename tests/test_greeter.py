import functools

import pytest

import purerpc

from purerpc.test_utils import (
    run_purerpc_service_in_process, run_grpc_service_in_process, async_iterable_to_list, grpc_client_parallelize,
    purerpc_channel, purerpc_client_parallelize, grpc_channel
)

pytestmark = pytest.mark.anyio


def name_generator(greeter_pb2):
    names = ('Foo', 'Bar', 'Bat', 'Baz')
    for name in names:
        yield greeter_pb2.HelloRequest(name=name)


async def async_name_generator(greeter_pb2):
    for request in name_generator(greeter_pb2):
        yield request


@pytest.fixture(scope="module")
def purerpc_codegen_greeter_port(greeter_pb2, greeter_grpc):
    class Servicer(greeter_grpc.GreeterServicer):
        async def SayHello(self, message):
            return greeter_pb2.HelloReply(message="Hello, " + message.name)

        async def SayHelloGoodbye(self, message):
            yield greeter_pb2.HelloReply(message="Hello, " + message.name)
            yield greeter_pb2.HelloReply(message="Goodbye, " + message.name)

        async def SayHelloToManyAtOnce(self, messages):
            names = []
            async for message in messages:
                names.append(message.name)
            return greeter_pb2.HelloReply(message="Hello, " + ", ".join(names))

        async def SayHelloToMany(self, messages):
            async for message in messages:
                yield greeter_pb2.HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(Servicer().service) as port:
        yield port


@pytest.fixture(scope="module")
def purerpc_simple_greeter_port(greeter_pb2):
    service = purerpc.Service("Greeter")

    @service.rpc("SayHello")
    async def say_hello(message: greeter_pb2.HelloRequest) -> greeter_pb2.HelloReply:
        return greeter_pb2.HelloReply(message="Hello, " + message.name)

    @service.rpc("SayHelloGoodbye")
    async def say_hello_goodbye(message: greeter_pb2.HelloRequest) -> purerpc.Stream[greeter_pb2.HelloReply]:
        yield greeter_pb2.HelloReply(message="Hello, " + message.name)
        yield greeter_pb2.HelloReply(message="Goodbye, " + message.name)

    @service.rpc("SayHelloToManyAtOnce")
    async def say_hello_to_many_at_once(messages: purerpc.Stream[greeter_pb2.HelloRequest]) -> greeter_pb2.HelloReply:
        names = []
        async for message in messages:
            names.append(message.name)
        return greeter_pb2.HelloReply(message="Hello, " + ', '.join(names))

    @service.rpc("SayHelloToMany")
    async def say_hello_to_many(messages: purerpc.Stream[greeter_pb2.HelloRequest]) -> purerpc.Stream[greeter_pb2.HelloReply]:
        async for message in messages:
            yield greeter_pb2.HelloReply(message="Hello, " + message.name)


    with run_purerpc_service_in_process(service) as port:
        yield port


@pytest.fixture(scope="module")
def grpc_greeter_port(greeter_pb2, greeter_pb2_grpc):
    class Servicer(greeter_pb2_grpc.GreeterServicer):
        def SayHello(self, message, context):
            return greeter_pb2.HelloReply(message="Hello, " + message.name)

        def SayHelloGoodbye(self, message, context):
            yield greeter_pb2.HelloReply(message="Hello, " + message.name)
            yield greeter_pb2.HelloReply(message="Goodbye, " + message.name)

        def SayHelloToMany(self, messages, context):
            for message in messages:
                yield greeter_pb2.HelloReply(message="Hello, " + message.name)

        def SayHelloToManyAtOnce(self, messages, context):
            names = []
            for message in messages:
                names.append(message.name)
            return greeter_pb2.HelloReply(message="Hello, " + ", ".join(names))

    with run_grpc_service_in_process(functools.partial(
            greeter_pb2_grpc.add_GreeterServicer_to_server, Servicer())) as port:
        yield port


@pytest.fixture(scope="module",
                params=["purerpc_codegen_greeter_port", "purerpc_simple_greeter_port"])
def purerpc_greeter_port(request):
    return request.getfixturevalue(request.param)


@pytest.fixture(scope="module",
                params=["purerpc_codegen_greeter_port", "purerpc_simple_greeter_port", "grpc_greeter_port"])
def greeter_port(request):
    return request.getfixturevalue(request.param)


@grpc_client_parallelize(50)
@grpc_channel("purerpc_greeter_port")
def test_grpc_client_parallel(greeter_pb2, greeter_pb2_grpc, channel):
    stub = greeter_pb2_grpc.GreeterStub(channel)
    assert stub.SayHello(greeter_pb2.HelloRequest(name="World")).message == "Hello, World"
    assert [response.message for response in
            stub.SayHelloGoodbye(greeter_pb2.HelloRequest(name="World"))] == ["Hello, World", "Goodbye, World"]
    assert stub.SayHelloToManyAtOnce(name_generator(greeter_pb2)).message == "Hello, Foo, Bar, Bat, Baz"
    assert [response.message for response in stub.SayHelloToMany(name_generator(greeter_pb2))] == \
           ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]


@purerpc_channel("greeter_port")
@purerpc_client_parallelize(50)
async def test_purerpc_stub_client_parallel(greeter_pb2, greeter_grpc, channel):
    stub = greeter_grpc.GreeterStub(channel)
    assert (await stub.SayHello(greeter_pb2.HelloRequest(name="World"))).message == "Hello, World"
    assert [response.message for response in await async_iterable_to_list(
            stub.SayHelloGoodbye(greeter_pb2.HelloRequest(name="World")))] == ["Hello, World", "Goodbye, World"]
    assert (await stub.SayHelloToManyAtOnce(async_name_generator(greeter_pb2))).message == "Hello, Foo, Bar, Bat, Baz"
    assert [response.message for response in await async_iterable_to_list(
            stub.SayHelloToMany(async_name_generator(greeter_pb2)))] == \
           ["Hello, Foo", "Hello, Bar", "Hello, Bat", "Hello, Baz"]


@purerpc_channel("greeter_port")
@purerpc_client_parallelize(50)
async def test_purerpc_stream_client_parallel(greeter_pb2, channel):
    async def test_say_hello(client):
        stream = await client.rpc("SayHello", greeter_pb2.HelloRequest, greeter_pb2.HelloReply)
        await stream.send_message(greeter_pb2.HelloRequest(name="World"))
        await stream.close()
        assert (await stream.receive_message()).message == "Hello, World"
        assert await stream.receive_message() is None

    async def test_say_hello_goodbye(client):
        stream = await client.rpc("SayHelloGoodbye", greeter_pb2.HelloRequest, greeter_pb2.HelloReply)
        await stream.send_message(greeter_pb2.HelloRequest(name="World"))
        await stream.close()
        assert (await stream.receive_message()).message == "Hello, World"
        assert (await stream.receive_message()).message == "Goodbye, World"
        assert await stream.receive_message() is None

    async def test_say_hello_to_many(client):
        stream = await client.rpc("SayHelloToMany", greeter_pb2.HelloRequest, greeter_pb2.HelloReply)
        await stream.send_message(greeter_pb2.HelloRequest(name="Foo"))
        assert (await stream.receive_message()).message == "Hello, Foo"
        await stream.send_message(greeter_pb2.HelloRequest(name="Bar"))
        assert (await stream.receive_message()).message == "Hello, Bar"
        await stream.send_message(greeter_pb2.HelloRequest(name="Baz"))
        await stream.send_message(greeter_pb2.HelloRequest(name="World"))
        assert (await stream.receive_message()).message == "Hello, Baz"
        assert (await stream.receive_message()).message == "Hello, World"
        await stream.close()
        assert await stream.receive_message() is None

    async def test_say_hello_to_many_at_once(client):
        stream = await client.rpc("SayHelloToManyAtOnce", greeter_pb2.HelloRequest, greeter_pb2.HelloReply)
        await stream.send_message(greeter_pb2.HelloRequest(name="Foo"))
        await stream.send_message(greeter_pb2.HelloRequest(name="Bar"))
        await stream.send_message(greeter_pb2.HelloRequest(name="Baz"))
        await stream.send_message(greeter_pb2.HelloRequest(name="World"))
        await stream.close()
        assert (await stream.receive_message()).message == "Hello, Foo, Bar, Baz, World"
        assert await stream.receive_message() is None

    client = purerpc.Client("Greeter", channel)
    await test_say_hello(client)
    await test_say_hello_goodbye(client)
    await test_say_hello_to_many(client)
    await test_say_hello_to_many_at_once(client)
