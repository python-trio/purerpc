import asyncio
import uuid
import logging
import inspect
import h2.config
import h2.connection
import h2.events
import h2.errors
import h2.exceptions
import collections
import typing
from google.protobuf.message import Message
from typing import Union
from .stream import Stream, MessageReader, MessageWriter, MessageReaderBuffer

logger = logging.getLogger(__name__)


# TODO: beware async generators and generators:
# https://vorpus.org/blog/some-thoughts-on-asynchronous-api-design-in-a-post-asyncawait-world/#cleanup-in-generators-and-async-generators


class CallbackWrapper:
    def __init__(self, in_type: Message, rpc_callback):
        self.in_type = in_type
        self.rpc_callback = rpc_callback

    async def callback_unary_unary(self, message_reader_buffer: MessageReaderBuffer,
                                   message_writer: MessageWriter):
        message_reader = MessageReader(self.in_type, message_reader_buffer)
        messages = []
        async for message in message_reader:
            messages.append(message)
        assert (len(messages) == 1)
        result = await self.rpc_callback(messages[0])
        message_writer.write(result)

    async def callback_unary_stream(self, message_reader_buffer: MessageReaderBuffer,
                                    message_writer: MessageWriter):
        message_reader = MessageReader(self.in_type, message_reader_buffer)
        messages = []
        async for message in message_reader:
            messages.append(message)
        assert (len(messages) == 1)
        if len(inspect.signature(self.rpc_callback).parameters) == 2:
            await self.rpc_callback(messages[0], message_writer)
        else:
            async for message in self.rpc_callback(messages[0]):
                message_writer.write(message)

    async def callback_stream_unary(self, message_reader_buffer: MessageReaderBuffer,
                                    message_writer: MessageWriter):
        message_reader = MessageReader(self.in_type, message_reader_buffer)
        result = await self.rpc_callback(message_reader)
        message_writer.write(result)

    async def callback_stream_stream(self, message_reader_buffer: MessageReaderBuffer,
                                     message_writer: MessageWriter):
        message_reader = MessageReader(self.in_type, message_reader_buffer)
        if len(inspect.signature(self.rpc_callback).parameters) == 2:
            await self.rpc_callback(message_reader, message_writer)
        else:
            async for message in self.rpc_callback(message_reader):
                message_writer.write(message)

    @property
    def callbacks(self):
        return {
            "unary": {
                "unary": self.callback_unary_unary,
                "stream": self.callback_unary_stream,
            },
            "stream": {
                "unary": self.callback_stream_unary,
                "stream": self.callback_stream_stream,
            }
        }


class Service:
    def __init__(self, service_name: str, host: str, port: int,
                 loop: asyncio.AbstractEventLoop = None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._service_name = service_name
        self._host = host
        self._port = port
        self._loop = loop
        self._methods = {}

    @property
    def loop(self):
        return self._loop

    @property
    def service_name(self):
        return self._service_name

    @property
    def methods(self):
        return self._methods

    def rpc(self, method_name: str, in_type: Union[type, Stream],
            out_type: Union[type, Stream]):
        def decorator(rpc_callback):
            callback_wrapper = CallbackWrapper(in_type.item_type if isinstance(in_type, Stream)
                                               else in_type, rpc_callback)

            callbacks_dict = callback_wrapper.callbacks

            if isinstance(in_type, Stream):
                callbacks_dict = callbacks_dict["stream"]
            else:
                callbacks_dict = callbacks_dict["unary"]

            if isinstance(out_type, Stream):
                new_rpc_callback = callbacks_dict["stream"]
            else:
                new_rpc_callback = callbacks_dict["unary"]

            self._methods[method_name] = new_rpc_callback
            return new_rpc_callback
        return decorator

    def serve(self):
        task = asyncio.start_server(lambda reader, writer: ConnectionHandler(self)(reader, writer),
                                    host=self._host, port=self._port, loop=self._loop)
        server = self._loop.run_until_complete(task)
        logger.info("Listening on {}".format(server.sockets))
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass

        server.close()
        self._loop.run_until_complete(server.wait_closed())
        self._loop.close()


RequestContext = typing.NamedTuple("RequestContext",
                                   (("method_name", str),
                                    ("stream_id", int),
                                    ("message_reader_buffer", MessageReaderBuffer),
                                    ("message_writer", MessageWriter)))


class ConnectionHandler:
    def __init__(self, service):
        self.service = service
        config = h2.config.H2Configuration(client_side=False, header_encoding="utf-8")
        self.connection = h2.connection.H2Connection(config=config)
        self.request_contexts = {}  # type: typing.Dict[int, RequestContext]

    async def handle_request(self, request_context: RequestContext):
        self.connection.send_headers(request_context.stream_id, (
            (':status', '200'),
            ('content-type', 'application/grpc+proto'),
            ('server', 'asyncio-h2-grpc'),
        ), end_stream=False)
        try:
            await self.service.methods[request_context.method_name](
                request_context.message_reader_buffer,
                request_context.message_writer
            )
        except Exception as e:
            logger.exception("Exception handling RPC call")
            request_context.message_writer.close_response(1, "Got exception: ".format(e))
        else:
            request_context.message_writer.close_response()

    def request_received(self, event: h2.events.RequestReceived, writer: asyncio.StreamWriter):
        headers = collections.OrderedDict(event.headers)
        _, service_name, method_name = headers[":path"].split("/")
        assert self.service.service_name == service_name

        request_context = RequestContext(method_name, event.stream_id, MessageReaderBuffer(),
                                         MessageWriter(self.connection, event.stream_id, writer))
        asyncio.ensure_future(self.handle_request(request_context), loop=self.service.loop)
        self.request_contexts[event.stream_id] = request_context

    def data_received(self, event: h2.events.DataReceived):
        try:
            self.request_contexts[event.stream_id].message_reader_buffer.write(event.data)
        except KeyError:
            self.connection.reset_stream(event.stream_id, h2.errors.ErrorCodes.PROTOCOL_ERROR)
        else:
            self.connection.acknowledge_received_data(event.flow_controlled_length, event.stream_id)

    def stream_ended(self, event: h2.events.StreamEnded):
        try:
            self.request_contexts[event.stream_id].message_reader_buffer.close()
        except KeyError:
            self.connection.reset_stream(event.stream_id, h2.errors.ErrorCodes.PROTOCOL_ERROR)

    async def __call__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            self.connection.initiate_connection()
            writer.write(self.connection.data_to_send())

            while True:
                data = await reader.read(1024)
                if not data:
                    return

                try:
                    events = self.connection.receive_data(data)
                except h2.exceptions.ProtocolError as e:
                    logger.error("Gor protocol error: {}".format(e))
                    return
                else:
                    for event in events:
                        if isinstance(event, h2.events.RequestReceived):
                            self.request_received(event, writer)
                        elif isinstance(event, h2.events.DataReceived):
                            self.data_received(event)
                        elif isinstance(event, h2.events.StreamEnded):
                            self.stream_ended(event)
                        elif isinstance(event, h2.events.ConnectionTerminated):
                            return
                        else:
                            logger.warning("Unhandled event: {}".format(event))
                        writer.write(self.connection.data_to_send())

        finally:
            writer.write(self.connection.data_to_send())
            await writer.drain()
            writer.close()
