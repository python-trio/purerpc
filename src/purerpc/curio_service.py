import sys
import curio
import logging
from .grpclib.connection import GRPCConfiguration, GRPCConnection
from .grpclib.events import MessageReceived, RequestReceived, RequestEnded
from async_generator import async_generator, yield_


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

    @async_generator
    async def deserializing_iterator(self, input_stream: curio.Queue):
        async for data in input_stream:
            if data is None:
                return
            message = self.in_type()
            message.ParseFromString(data)
            await yield_(message)

    @async_generator
    async def __call__(self, input_queue: curio.Queue):
        iter = self.deserializing_iterator(input_queue)
        async with AClosing(self.rpc_callback(iter)) as temp:
            async for message in temp:
                await yield_(message.SerializeToString())


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
        await curio.tcp_server('', self.port, lambda c, a: ConnectionHandler(self)(c, a),
                               reuse_address=True, reuse_port=True)


class ConnectionHandler:
    RECEIVE_BUFFER_SIZE = 65536

    def __init__(self, service: Service):

        config = GRPCConfiguration(client_side=False)
        self.connection = GRPCConnection(config=config)
        self.service = service

        self.request_message_queue = {}

        self.write_event = curio.Event()
        self.write_shutdown = False
        self.stream = None

    async def stream_writer(self):
        # TODO: this should be the single thread that writes to self.stream, communication with
        # this thread should go through special event self.write_event
        # The logic is simple:
        # while True:
        #   while self.connection.data_to_send() > 0:
        #      await self.stream.sendall(...)
        #   await self.write_event.wait()
        # TODO: second option: use StrictFIFOLock and write data in the threads that generate it
        while True:
            await self.write_event.wait()
            self.write_event.clear()
            while True:
                data = self.connection.data_to_send()
                if not data:
                    break
                await self.stream.sendall(data)
            if self.write_shutdown:
                return

    async def ping_writer(self):
        await self.write_event.set()

    async def request_received(self, event: RequestReceived):
        self.connection.start_response(event.stream_id, "+proto")
        await self.ping_writer()

        try:
            async for message in self.service.methods[event.method_name](self.request_message_queue[event.stream_id]):
                self.connection.send_message(event.stream_id, message)
                await self.ping_writer()

            self.connection.end_response(event.stream_id, 0)
            await self.ping_writer()
        except:
            logging.exception("Got exception while writing response stream")
            self.connection.end_response(event.stream_id, 1, status_message=repr(sys.exc_info()))
            await self.ping_writer()
        finally:
            del self.request_message_queue[event.stream_id]

    async def message_received(self, event: MessageReceived):
        await self.request_message_queue[event.stream_id].put(event.data)

    async def request_ended(self, event: RequestEnded):
        await self.request_message_queue[event.stream_id].put(None)

    async def __call__(self, client, addr):
        self.stream = client
        await curio.spawn(self.stream_writer(), daemon=True)
        self.connection.initiate_connection()
        await self.ping_writer()

        task_group = curio.TaskGroup()
        try:
            while True:
                data = await client.recv(self.RECEIVE_BUFFER_SIZE)
                if not data:
                    return
                events = self.connection.receive_data(data)
                for event in events:
                    if isinstance(event, RequestReceived):
                        # start RPC thread
                        self.request_message_queue[event.stream_id] = curio.Queue(10)
                        await task_group.spawn(self.request_received, event)
                    elif isinstance(event, RequestEnded):
                        await self.request_ended(event)
                    elif isinstance(event, MessageReceived):
                        await self.message_received(event)
                await self.ping_writer()
        except:
            logging.exception("Got exception in main dispatch loop")
        finally:
            await task_group.join()
            self.write_shutdown = True
            await self.ping_writer()
