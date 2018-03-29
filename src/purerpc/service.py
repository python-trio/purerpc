import sys
import trio
import logging
import collections
from .grpclib.connection import GRPCConfiguration, GRPCConnection
from .grpclib.events import MessageReceived, RequestReceived, RequestEnded


class MessageStream:
    def __init__(self):
        self.message_deque = collections.deque()
        self.closed = False
        self.data_ready_event = trio.Event()

    def put(self, item):
        self.message_deque.append(item)
        self.data_ready_event.set()

    def close(self):
        self.closed = True
        self.data_ready_event.set()

    async def __aiter__(self):
        return self

    async def __anext__(self):
        if self.closed:
            raise StopAsyncIteration
        while not self.message_deque:
            await self.data_ready_event.wait()
            if self.closed:
                raise StopAsyncIteration
        return self.message_deque.popleft()


class AClosing:
    def __init__(self, agen):
        self._agen = agen

    async def __aenter__(self):
        return self._agen

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._agen.aclose()


class CallbackWrapper:
    def __init__(self, in_type, rpc_callback):
        self.in_type = in_type
        self.rpc_callback = rpc_callback

    async def deserializing_iterator(self, input_stream: MessageStream):
        async for data in input_stream:
            message = self.in_type()
            message.ParseFromString(data)
            yield message

    async def __call__(self, input_stream: MessageStream):
        iter = self.deserializing_iterator(input_stream)
        async with AClosing(self.rpc_callback(iter)) as temp:
            async for message in temp:
                yield message.SerializeToString()


class Service:
    def __init__(self, port=50055):
        self.port = port
        self.methods = {}

    def rpc(self, method_name, InputMessageType):
        def decorator(rpc_callback):
            wrapper = CallbackWrapper(InputMessageType, rpc_callback)
            self.methods[method_name] = wrapper
            return wrapper
        return decorator

    async def __call__(self):
        await trio.serve_tcp(lambda stream: ConnectionHandler(self)(stream), self.port)


class ConnectionHandler:
    RECEIVE_BUFFER_SIZE = 65536

    def __init__(self, service: Service):
        config = GRPCConfiguration(client_side=False)
        self.connection = GRPCConnection(config=config)
        self.service = service

        self.request_message_streams = {}

        self.write_lock = trio.Lock()
        self.stream = None

    async def write_all_pending_data(self):
        async with self.write_lock:
            await self.stream.send_all(self.connection.data_to_send())

    async def request_received(self, event: RequestReceived):
        input_stream = MessageStream()
        self.request_message_streams[event.stream_id] = input_stream
        self.connection.start_response(event.stream_id, "+proto")
        await self.write_all_pending_data()

        try:
            async for message in self.service.methods[event.method_name](input_stream):
                self.connection.send_message(event.stream_id, message)
                await self.write_all_pending_data()

            print("Ending response")
            self.connection.end_response(event.stream_id, 0)
            await self.write_all_pending_data()
        except:
            logging.exception("Got exception while writing response stream")
            self.connection.end_response(event.stream_id, 1, status_message=repr(sys.exc_info()))
            await self.write_all_pending_data()

    def message_received(self, event: MessageReceived):
        self.request_message_streams[event.stream_id].put(event.data)

    def request_ended(self, event: RequestEnded):
        self.request_message_streams[event.stream_id].close()

    async def __call__(self, server_stream):
        self.stream = server_stream
        try:
            self.connection.initiate_connection()
            await self.write_all_pending_data()

            try:
                async with trio.open_nursery() as nursery:
                    while True:
                        data = await server_stream.receive_some(self.RECEIVE_BUFFER_SIZE)
                        if not data:
                            return
                        events = self.connection.receive_data(data)
                        for event in events:
                            if isinstance(event, RequestReceived):
                                nursery.start_soon(self.request_received, event)
                            elif isinstance(event, RequestEnded):
                                self.request_ended(event)
                            elif isinstance(event, MessageReceived):
                                self.message_received(event)
                            await self.write_all_pending_data()
            finally:
                await self.write_all_pending_data()
        except:
            logging.exception("Got exception in main dispatch loop")
