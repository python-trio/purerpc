import sys
import trio
import logging
import collections
from .grpclib.connection import GRPCConfiguration, GRPCConnection
from .grpclib.events import MessageReceived, RequestReceived, RequestEnded


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

    async def deserializing_iterator(self, input_stream: trio.Queue):
        async for data in input_stream:
            if data is None:
                return
            message = self.in_type()
            message.ParseFromString(data)
            yield message

    async def __call__(self, input_queue: trio.Queue):
        iter = self.deserializing_iterator(input_queue)
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

        logging.info("Constructing connection handler")
        config = GRPCConfiguration(client_side=False)
        self.connection = GRPCConnection(config=config)
        self.service = service

        self.request_message_queue = {}

        self.write_event = trio.Event()
        self.write_shutdown = False
        self.stream = None

    async def stream_writer(self, *, task_status=trio.TASK_STATUS_IGNORED):
        # TODO: this should be the single thread that writes to self.stream, communication with
        # this thread should go through special event self.write_event
        # The logic is simple:
        # while True:
        #   while self.connection.data_to_send() > 0:
        #      await self.stream.sendall(...)
        #   await self.write_event.wait()
        # TODO: second option: use StrictFIFOLock and write data in the threads that generate it
        task_status.started()
        while True:
            await self.write_event.wait()
            while True:
                data = self.connection.data_to_send()
                if not data:
                    break
                logging.info("Sending {}".format(data))
                await self.stream.send_all(data)
            if self.write_shutdown:
                return

    async def ping_writer(self):
        self.write_event.set()
        await trio.sleep(0)

    async def request_received(self, event: RequestReceived, *,
                               task_status=trio.TASK_STATUS_IGNORED):
        input_queue = trio.Queue(10)
        logging.info("Creating message queue for {}".format(event.stream_id))
        self.request_message_queue[event.stream_id] = input_queue
        self.connection.start_response(event.stream_id, "+proto")
        task_status.started()
        await self.ping_writer()

        try:
            async for message in self.service.methods[event.method_name](input_queue):
                self.connection.send_message(event.stream_id, message)
                await self.ping_writer()

            print("Ending response")
            self.connection.end_response(event.stream_id, 0)
            await self.ping_writer()
        except:
            logging.exception("Got exception while writing response stream")
            self.connection.end_response(event.stream_id, 1, status_message=repr(sys.exc_info()))
            await self.ping_writer()

    async def message_received(self, event: MessageReceived):
        logging.info("Message received {}".format(event.data))
        await self.request_message_queue[event.stream_id].put(event.data)

    async def request_ended(self, event: RequestEnded):
        await self.request_message_queue[event.stream_id].put(None)
        logging.info("Deleting message queue for {}".format(event.stream_id))
        del self.request_message_queue[event.stream_id]

    async def __call__(self, server_stream):
        logging.info("In __call__")
        self.stream = server_stream
        try:
            async with trio.open_nursery() as nursery:
                await nursery.start(self.stream_writer)
                self.connection.initiate_connection()
                await self.ping_writer()

                try:
                    while True:
                        data = await server_stream.receive_some(self.RECEIVE_BUFFER_SIZE)
                        if not data:
                            return
                        events = self.connection.receive_data(data)
                        for event in events:
                            if isinstance(event, RequestReceived):
                                # start RPC thread
                                await nursery.start(self.request_received, event)
                            elif isinstance(event, RequestEnded):
                                await self.request_ended(event)
                            elif isinstance(event, MessageReceived):
                                await self.message_received(event)
                        await self.ping_writer()
                finally:
                    self.write_shutdown = True
                    await self.ping_writer()
        except:
            logging.exception("Got exception in main dispatch loop")
