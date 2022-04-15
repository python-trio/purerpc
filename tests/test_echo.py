import functools
import ssl

import pytest
import trustme
from async_generator import async_generator, yield_

import purerpc
from purerpc.test_utils import run_purerpc_service_in_process, run_grpc_service_in_process, \
    async_iterable_to_list, random_payload, grpc_client_parallelize, async_test, purerpc_channel, purerpc_client_parallelize, grpc_channel


@pytest.fixture(scope='module')
def ca():
    return trustme.CA()


@pytest.fixture(scope='module')
def server_ssl_context(ca):
    server_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ca.issue_cert('127.0.0.1').configure_cert(server_context)
    return server_context


@pytest.fixture(scope='module')
def client_ssl_context(ca):
    client_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ca.configure_trust(client_context)
    return client_context


@pytest.fixture(scope="module")
def purerpc_echo_port(echo_pb2, echo_grpc):
    class Servicer(echo_grpc.EchoServicer):
        async def Echo(self, message):
            return echo_pb2.EchoReply(data=message.data)

        @async_generator
        async def EchoTwoTimes(self, message):
            await yield_(echo_pb2.EchoReply(data=message.data))
            await yield_(echo_pb2.EchoReply(data=message.data))

        @async_generator
        async def EchoEachTime(self, messages):
            async for message in messages:
                await yield_(echo_pb2.EchoReply(data=message.data))

        async def EchoLast(self, messages):
            data = []
            async for message in messages:
                data.append(message.data)
            return echo_pb2.EchoReply(data="".join(data))

        @async_generator
        async def EchoLastV2(self, messages):
            data = []
            async for message in messages:
                data.append(message.data)
            await yield_(echo_pb2.EchoReply(data="".join(data)))

    with run_purerpc_service_in_process(Servicer().service) as port:
        # TODO: migrate to serve_async() to avoid timing problems
        import time
        time.sleep(.1)
        yield port


@pytest.fixture(scope="module")
def purerpc_echo_port_ssl(echo_pb2, echo_grpc, server_ssl_context):
    class Servicer(echo_grpc.EchoServicer):
        async def Echo(self, message):
            return echo_pb2.EchoReply(data=message.data)

        @async_generator
        async def EchoTwoTimes(self, message):
            await yield_(echo_pb2.EchoReply(data=message.data))
            await yield_(echo_pb2.EchoReply(data=message.data))

        @async_generator
        async def EchoEachTime(self, messages):
            async for message in messages:
                await yield_(echo_pb2.EchoReply(data=message.data))

        async def EchoLast(self, messages):
            data = []
            async for message in messages:
                data.append(message.data)
            return echo_pb2.EchoReply(data="".join(data))

        @async_generator
        async def EchoLastV2(self, messages):
            data = []
            async for message in messages:
                data.append(message.data)
            await yield_(echo_pb2.EchoReply(data="".join(data)))

    with run_purerpc_service_in_process(Servicer().service,
                                        ssl_context=server_ssl_context) as port:
        # TODO: migrate to serve_async() to avoid timing problems
        import time
        time.sleep(.1)
        yield port


@pytest.fixture(scope="module")
def grpc_echo_port(echo_pb2, echo_pb2_grpc):
    class Servicer(echo_pb2_grpc.EchoServicer):
        def Echo(self, message, context):
            return echo_pb2.EchoReply(data=message.data)

        def EchoTwoTimes(self, message, context):
            yield echo_pb2.EchoReply(data=message.data)
            yield echo_pb2.EchoReply(data=message.data)

        def EchoEachTime(self, messages, context):
            for message in messages:
                yield echo_pb2.EchoReply(data=message.data)

        def EchoLast(self, messages, context):
            data = []
            for message in messages:
                data.append(message.data)
            return echo_pb2.EchoReply(data="".join(data))

        def EchoLastV2(self, messages, context):
            data = []
            for message in messages:
                data.append(message.data)
            yield echo_pb2.EchoReply(data="".join(data))

    with run_grpc_service_in_process(functools.partial(
            echo_pb2_grpc.add_EchoServicer_to_server, Servicer())) as port:
        yield port


@pytest.fixture(scope="module",
                params=["purerpc_echo_port", "grpc_echo_port"])
def echo_port(request):
    return request.getfixturevalue(request.param)


@async_test
@purerpc_channel("echo_port")
@purerpc_client_parallelize(50)
async def test_purerpc_client_large_payload_many_streams(echo_pb2, echo_grpc, channel):
    stub = echo_grpc.EchoStub(channel)
    data = "World" * 20000
    assert (await stub.Echo(echo_pb2.EchoRequest(data=data))).data == data


@async_test
@purerpc_channel("echo_port")
async def test_purerpc_client_large_payload_one_stream(echo_pb2, echo_grpc, channel):
    stub = echo_grpc.EchoStub(channel)
    data = "World" * 20000
    assert (await stub.Echo(echo_pb2.EchoRequest(data=data))).data == data


@grpc_client_parallelize(50)
@grpc_channel("echo_port")
def test_grpc_client_large_payload(echo_pb2, echo_pb2_grpc, channel):
    stub = echo_pb2_grpc.EchoStub(channel)
    data = "World" * 20000
    assert stub.Echo(echo_pb2.EchoRequest(data=data)).data == data


@async_test
@purerpc_channel("echo_port")
@purerpc_client_parallelize(20)
async def test_purerpc_client_random_payload(echo_pb2, echo_grpc, channel):
    stub = echo_grpc.EchoStub(channel)
    data = random_payload()

    @async_generator
    async def gen():
        for _ in range(4):
            await yield_(echo_pb2.EchoRequest(data=data))

    assert (await stub.Echo(echo_pb2.EchoRequest(data=data))).data == data
    assert [response.data for response in await async_iterable_to_list(
            stub.EchoTwoTimes(echo_pb2.EchoRequest(data=data)))] == [data] * 2
    assert (await stub.EchoLast(gen())).data == data * 4
    assert [response.data for response in await async_iterable_to_list(
            stub.EchoEachTime(gen()))] == [data] * 4


@async_test
@purerpc_channel("echo_port")
@purerpc_client_parallelize(10)
async def test_purerpc_client_deadlock(echo_pb2, echo_grpc, channel):
    stub = echo_grpc.EchoStub(channel)
    data = random_payload(min_size=32000, max_size=64000)

    @async_generator
    async def gen():
        for _ in range(20):
            await yield_(echo_pb2.EchoRequest(data=data))

    assert [response.data for response in await async_iterable_to_list(
            stub.EchoLastV2(gen()))] == [data * 20]


@async_test
async def test_purerpc_ssl(echo_pb2, echo_grpc, purerpc_echo_port_ssl, client_ssl_context):
    async with purerpc.secure_channel("127.0.0.1", purerpc_echo_port_ssl,
                                      ssl_context=client_ssl_context) as channel:
        stub = echo_grpc.EchoStub(channel)
        data = random_payload(min_size=32000, max_size=64000)

        @async_generator
        async def gen():
            for _ in range(20):
                await yield_(echo_pb2.EchoRequest(data=data))

        assert [response.data for response in await async_iterable_to_list(
                stub.EchoLastV2(gen()))] == [data * 20]
