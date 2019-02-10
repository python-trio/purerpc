import functools

import anyio
from async_generator import aclosing, async_generator, asynccontextmanager, yield_, yield_from_

from .grpclib.exceptions import ProtocolError, raise_status
from .grpclib.status import Status, StatusCode
from purerpc.grpc_proto import GRPCProtoStream
from purerpc.grpclib.events import ResponseEnded


async def extract_message_from_singleton_stream(stream):
    msg = await stream.receive_message()
    if msg is None:
        event = stream.end_stream_event
        if isinstance(event, ResponseEnded):
            raise_status(event.status)
        raise ProtocolError("Expected one message, got zero")
    if await stream.receive_message() is not None:
        raise ProtocolError("Expected one message, got multiple")
    return msg


@async_generator
async def stream_to_async_iterator(stream: GRPCProtoStream):
    while True:
        msg = await stream.receive_message()
        if msg is None:
            event = stream.end_stream_event
            if isinstance(event, ResponseEnded):
                raise_status(event.status)
            return
        await yield_(msg)


async def send_multiple_messages_server(stream, aiter):
    async with aclosing(aiter) as aiter:
        async for message in aiter:
            await stream.send_message(message)
    await stream.close(Status(StatusCode.OK))


async def send_single_message_server(stream, message):
    await stream.send_message(message)
    await stream.close(Status(StatusCode.OK))


async def send_multiple_messages_client(stream, aiter):
    try:
        async with aclosing(aiter) as aiter:
            async for message in aiter:
                await stream.send_message(message)
    finally:
        await stream.close()


async def send_single_message_client(stream, message):
    try:
        await stream.send_message(message)
    finally:
        await stream.close()


async def call_server_unary_unary(func, stream):
    msg = await extract_message_from_singleton_stream(stream)
    await send_single_message_server(stream, await func(msg))


async def call_server_unary_stream(func, stream):
    msg = await extract_message_from_singleton_stream(stream)
    await send_multiple_messages_server(stream, func(msg))


async def call_server_stream_unary(func, stream):
    input_message_stream = stream_to_async_iterator(stream)
    await send_single_message_server(stream, await func(input_message_stream))


async def call_server_stream_stream(func, stream):
    input_message_stream = stream_to_async_iterator(stream)
    await send_multiple_messages_server(stream, func(input_message_stream))


class ClientStub:
    def __init__(self, stream_fn):
        self._stream_fn = stream_fn


class ClientStubUnaryUnary(ClientStub):
    async def __call__(self, message, *, metadata=None):
        stream = await self._stream_fn(metadata=metadata)
        await send_single_message_client(stream, message)
        return await extract_message_from_singleton_stream(stream)


class ClientStubUnaryStream(ClientStub):
    @async_generator
    async def __call__(self, message, *, metadata=None):
        stream = await self._stream_fn(metadata=metadata)
        await send_single_message_client(stream, message)
        await yield_from_(stream_to_async_iterator(stream))


class ClientStubStreamUnary(ClientStub):
    async def __call__(self, message_aiter, *, metadata=None):
        stream = await self._stream_fn(metadata=metadata)
        async with anyio.create_task_group() as task_group:
            await task_group.spawn(send_multiple_messages_client, stream, message_aiter)
            return await extract_message_from_singleton_stream(stream)


class ClientStubStreamStream(ClientStub):
    @async_generator
    async def call_aiter(self, message_aiter, metadata):
        stream = await self._stream_fn(metadata=metadata)
        async with anyio.create_task_group() as task_group:
            await task_group.spawn(send_multiple_messages_client, stream, message_aiter)
            await yield_from_(stream_to_async_iterator(stream))

    async def call_stream(self, metadata):
        return await self._stream_fn(metadata=metadata)

    def __call__(self, message_aiter=None, *, metadata=None):
        if message_aiter is None:
            return self.call_stream(metadata)
        else:
            return self.call_aiter(message_aiter, metadata)
