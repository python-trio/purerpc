import curio
import socket
import curio.io
import datetime
import collections
import h2
import h2.events
from purerpc.utils import is_darwin
from purerpc.grpclib.exceptions import ProtocolError

from .grpclib.connection import GRPCConfiguration, GRPCConnection
from .grpclib.events import RequestReceived, RequestEnded, ResponseEnded, MessageReceived
from .grpclib.buffers import MessageWriteBuffer, MessageReadBuffer


class SocketWrapper:
    def __init__(self, grpc_connection: GRPCConnection, sock: curio.io.Socket):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, "TCP_KEEPIDLE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 300)
        elif is_darwin():
            # Darwin specific option
            TCP_KEEPALIVE = 16
            sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, 300)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._socket = sock
        self._grpc_connection = grpc_connection
        self._write_fifo_lock = curio.Lock()
        self._retry = False

    async def flush(self):
        """This maybe called from different threads."""
        async with self._write_fifo_lock:
            self._retry = True
            while self._retry:
                self._retry = False
                data = self._grpc_connection.data_to_send()
                if not data:
                    return
                await self._socket.sendall(data)

    async def try_flush(self):
        if self.locked:
            self._retry = True
        else:
            await self.flush()

    @property
    def locked(self):
        return self._write_fifo_lock.locked()

    async def recv(self, buffer_size: int):
        """This may only be called from single thread."""
        return await self._socket.recv(buffer_size)


class GRPCStream:
    def __init__(self, grpc_connection: GRPCConnection, stream_id: int, socket: SocketWrapper,
                 grpc_socket: "GRPCSocket"):
        self._stream_id = stream_id
        self._grpc_connection = grpc_connection
        self._grpc_socket = grpc_socket
        self._socket = socket
        self._flow_control_update_event = curio.Event()
        self._incoming_events = curio.Queue()

        self._response_started = False
        self._closed = False
        
        self._start_stream_event = None
        self._end_stream_event = None

    @property
    def start_stream_event(self):
        return self._start_stream_event

    @property
    def end_stream_event(self):
        return self._end_stream_event

    @property
    def flow_control_update_event(self):
        return self._flow_control_update_event

    @property
    def incoming_events(self):
        return self._incoming_events

    @property
    def stream_id(self):
        return self._stream_id

    @property
    def client_side(self):
        return self._grpc_connection.config.client_side

    @property
    def debug_prefix(self):
        return "[CLIENT] " if self.client_side else "[SERVER] "

    async def _send(self, message: bytes, compress=False):
        message_write_buffer = MessageWriteBuffer(self._grpc_connection.config.message_encoding,
                                                  self._grpc_connection.config.max_message_length)
        message_write_buffer.write_message(message, compress)
        while message_write_buffer:
            window_size = self._grpc_connection.flow_control_window(self._stream_id)
            if window_size <= 0:
                await self._flow_control_update_event.wait()
                self._flow_control_update_event.clear()
                continue
            num_data_to_send = min(window_size, len(message_write_buffer))
            data = message_write_buffer.data_to_send(num_data_to_send)
            self._grpc_connection.send_data(self._stream_id, data)
            await self._socket.flush()

    async def _receive(self):
        event = await self._incoming_events.get()
        if isinstance(event, MessageReceived):
            self._grpc_connection.acknowledge_received_data(self._stream_id,
                                                            event.flow_controlled_length)
            await self._socket.flush()
        elif isinstance(event, RequestEnded) or isinstance(event, ResponseEnded):
            assert self._end_stream_event is None
            self._end_stream_event = event
        else:
            assert self._start_stream_event is None
            self._start_stream_event = event
        return event

    async def close(self, status=None, content_type_suffix="", custom_metadata=()):
        if self.client_side and (status or custom_metadata):
            raise ValueError("Client side streams cannot be closed with non-default arguments")
        if self._closed:
            raise TypeError("Closing already closed stream")
        self._closed = True
        if self.client_side:
            self._grpc_connection.end_request(self._stream_id)
        elif self._response_started:
            self._grpc_connection.end_response(self._stream_id, status, custom_metadata)
        else:
            self._grpc_connection.respond_status(self._stream_id, status,
                                                 content_type_suffix, custom_metadata)
        await self._socket.flush()
        self._grpc_socket._decref_stream(self._stream_id)

    async def start_response(self, content_type_suffix="", custom_metadata=()):
        if self.client_side:
            raise ValueError("Cannot start response on client-side socket")
        self._grpc_connection.start_response(self._stream_id, content_type_suffix, custom_metadata)
        self._response_started = True
        await self._socket.flush()


# TODO: this name is not correct, should be something like GRPCConnection (but this name is already
# occupied)
class GRPCSocket:
    StreamClass = GRPCStream

    def __init__(self, config: GRPCConfiguration, sock: curio.io.Socket,
                 receive_buffer_size=16384):
        self._grpc_connection = GRPCConnection(config=config)
        self._socket = SocketWrapper(self._grpc_connection, sock)
        self._receive_buffer_size = receive_buffer_size

        self._streams = {}  # type: Dict[int, GRPCStream]
        self._streams_count = {}  # type: Dict[int, int]

    @property
    def client_side(self):
        return self._grpc_connection.config.client_side

    def _stream_ctor(self, stream_id):
        return self.StreamClass(self._grpc_connection, stream_id, self._socket, self)

    def _allocate_stream(self, stream_id):
        stream = self._stream_ctor(stream_id)
        self._streams[stream_id] = stream
        self._streams_count[stream_id] = 2
        return stream

    def _decref_stream(self, stream_id: int):
        self._streams_count[stream_id] -= 1
        if self._streams_count[stream_id] == 0:
            del self._streams[stream_id]
            del self._streams_count[stream_id]

    async def _listen(self):
        while True:
            data = await self._socket.recv(self._receive_buffer_size)
            if not data:
                return
            events = self._grpc_connection.receive_data(data)
            for event in events:
                # TODO: implement this
                if isinstance(event, h2.events.WindowUpdated):
                    if event.stream_id == 0:
                        for stream in self._streams.values():
                            await stream.flow_control_update_event.set()
                    elif event.stream_id in self._streams:
                        await self._streams[event.stream_id].flow_control_update_event.set()
                    continue
                elif isinstance(event, RequestReceived):
                    self._allocate_stream(event.stream_id)

                await self._streams[event.stream_id]._incoming_events.put(event)

                if isinstance(event, RequestReceived):
                    yield self._streams[event.stream_id]
                elif isinstance(event, ResponseEnded) or isinstance(event, RequestEnded):
                    self._decref_stream(event.stream_id)
            await self._socket.try_flush()

    async def _listener_thread(self):
        async for _ in self._listen():
            raise ProtocolError("Received request on client end")

    async def initiate_connection(self):
        self._grpc_connection.initiate_connection()
        await self._socket.flush()
        if self.client_side:
            await curio.spawn(self._listener_thread(), daemon=True)

    async def listen(self):
        if self.client_side:
            raise ValueError("Cannot listen client-side socket")
        async for stream in self._listen():
            yield stream

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
        await self._socket.flush()
        return stream
