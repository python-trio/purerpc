import curio
import curio.io
import datetime
import collections
from purerpc.grpclib.exceptions import ProtocolError

from .grpclib.connection import GRPCConfiguration, GRPCConnection
from .grpclib.events import (
    RequestReceived, RequestEnded, MessageReceived, ResponseReceived, ResponseEnded)


StreamClose = collections.namedtuple("StreamClose", ["status", "status_message", "custom_metadata"])


class GRPCStream:
    def __init__(self, socket: "GRPCSocket", stream_id: int, client_side: bool,
                 incoming_buffer_size=10, outgoing_buffer_size=10):
        self._socket = socket
        self._stream_id = stream_id
        self._client_side = client_side
        self._incoming_events = curio.Queue(incoming_buffer_size)
        self._outgoing_messages = curio.Queue(outgoing_buffer_size)

    @property
    def stream_id(self):
        return self._stream_id

    @property
    def client_side(self):
        return self._client_side

    async def send(self, message):
        await self._outgoing_messages.put(message)
        await self._socket._write_event.set()

    async def recv(self) -> "Event":
        return await self._incoming_events.get()

    async def close(self, status=None, status_message=None, custom_metadata=()):
        if self._client_side and (status or status_message or custom_metadata):
            raise ValueError("Client side streams cannot be closed with non-default arguments")
        await self.send(StreamClose(status, status_message, custom_metadata))

    async def start_response(self, stream_id: int, content_type_suffix="", custom_metadata=()):
        if self._client_side:
            raise ValueError("Cannot start response on client-side socket")
        await self._socket._start_response(stream_id, content_type_suffix, custom_metadata)


class GRPCSocket:
    def __init__(self, config: GRPCConfiguration, socket: curio.io.Socket,
                 receive_buffer_size=65536):
        self._grpc_connection = GRPCConnection(config=config)
        self._write_event = curio.Event()
        self._write_shutdown = False
        self._socket = socket
        self._receive_buffer_size = receive_buffer_size

        self._streams = {}  # type: Dict[int, GRPCStream]
        self._streams_count = {}  # type: Dict[int, int]

    @property
    def client_side(self):
        return self._grpc_connection.config.client_side

    def _allocate_stream(self, stream_id):
        stream = GRPCStream(self, stream_id, self.client_side)
        self._streams[stream_id] = stream
        self._streams_count[stream_id] = 2
        return stream

    def _decref_stream(self, stream_id: int):
        self._streams_count[stream_id] -= 1
        if self._streams_count[stream_id] == 0:
            del self._streams[stream_id]
            del self._streams_count[stream_id]

    async def _writer_thread(self):
        while True:
            await self._write_event.wait()
            self._write_event.clear()
            ended_streams = []
            for stream_id, stream in self._streams.items():
                while not stream._outgoing_messages.empty():
                    message = stream._outgoing_messages._get()
                    if isinstance(message, StreamClose):
                        if stream.client_side:
                            self._grpc_connection.end_request(stream_id)
                        else:
                            self._grpc_connection.end_response(stream_id, message.status,
                                                               message.status_message,
                                                               message.custom_metadata)
                        ended_streams.append(stream_id)
                    else:
                        self._grpc_connection.send_message(stream_id, message)
            for stream_id in ended_streams:
                self._decref_stream(stream_id)
            while True:
                data = self._grpc_connection.data_to_send()
                if not data:
                    break
                await self._socket.sendall(data)
            if self._write_shutdown:
                return

    async def _listen(self):
        while True:
            data = await self._socket.recv(self._receive_buffer_size)
            if not data:
                return
            events = self._grpc_connection.receive_data(data)
            for event in events:
                if isinstance(event, RequestReceived):
                    self._allocate_stream(event.stream_id)
                await self._streams[event.stream_id]._incoming_events.put(event)

                if isinstance(event, RequestReceived):
                    yield self._streams[event.stream_id]
                elif isinstance(event, ResponseEnded) or isinstance(event, RequestEnded):
                    self._decref_stream(event.stream_id)
            await self._write_event.set()

    async def _listener_thread(self):
        async for _ in self._listen():
            raise ProtocolError("Received request on client end")

    async def initiate_connection(self):
        self._grpc_connection.initiate_connection()
        await curio.spawn(self._writer_thread(), daemon=True)
        await self._write_event.set()
        if self.client_side:
            await curio.spawn(self._listener_thread(), daemon=True)

    async def shutdown(self):
        self._write_shutdown = True
        await self._write_event.set()

    async def listen(self):
        if self.client_side:
            raise ValueError("Cannot listen client-side socket")
        async for stream in self._listen():
            yield stream

    async def _start_response(self, stream_id: int, content_type_suffix="", custom_metadata=()):
        self._grpc_connection.start_response(stream_id, content_type_suffix, custom_metadata)
        await self._write_event.set()

    async def start_request(self, scheme: str, service_name: str, method_name: str,
                            message_type=None, authority=None, timeout: datetime.timedelta=None,
                            content_type_suffix="", custom_metadata=()):
        if not self.client_side:
            raise ValueError("Cannot start request on server-side socket")
        stream_id = self._grpc_connection.get_next_available_stream_id()
        stream = self._allocate_stream(stream_id)
        self._grpc_connection.start_request(stream_id, scheme, service_name, method_name,
                                            message_type, authority, timeout,
                                            content_type_suffix, custom_metadata)
        await self._write_event.set()
        return stream

