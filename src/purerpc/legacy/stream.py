import asyncio
import struct
import io
from google.protobuf.message import Message

from h2.connection import H2Connection


class Stream:
    def __init__(self, item_type):
        self.item_type = item_type


class MessageReaderBuffer:
    def __init__(self):
        self._buffer = bytearray()
        self._buffer_write_event = asyncio.Event()
        self._closed = False

    def close(self):
        self._closed = True
        self._buffer_write_event.set()

    def write(self, data: bytes):
        self._buffer.extend(data)
        self._buffer_write_event.set()

    async def _read(self):
        if self._closed:
            raise IOError("Trying to read from closed WriteBuffer")
        await self._buffer_write_event.wait()
        self._buffer_write_event.clear()

    async def read(self, num_bytes: int = -1):
        if num_bytes == -1:
            await self._read()
            result = bytes(self._buffer)
            self._buffer = bytearray()
        else:
            while len(self._buffer) < num_bytes:
                await self._read()
            result = bytes(self._buffer[:num_bytes])
            self._buffer = self._buffer[num_bytes:]
        return result


class MessageReader:
    def __init__(self, message_type: type(Message), write_buffer: MessageReaderBuffer):
        self._message_type = message_type
        self._write_buffer = write_buffer

    async def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            # TODO: actually need to throw StopAyncIteration only here and if buffer is empty
            # otherwise we got some data and then the buffer was closed, this may indicate some
            # error
            data = await self._write_buffer.read(5)

            compressed_flag = struct.unpack('?', data[0:1])[0]
            message_length = struct.unpack('>I', data[1:5])[0]

            if compressed_flag:
                raise NotImplementedError("Compression not implemented")

            data = await self._write_buffer.read(message_length)

            message = self._message_type()
            message.ParseFromString(data)
            return message
        except IOError:
            raise StopAsyncIteration


# TODO: decouple http/2 logic from serialization logic
class MessageWriter:
    def __init__(self, connection: H2Connection, stream_id: int, writer: asyncio.StreamWriter):
        self._connection = connection
        self._stream_id = stream_id
        self._writer = writer

    def write(self, message: Message):
        message_data = message.SerializeToString()
        # TODO: maybe move to faster bytearray or io.BytesIO()?
        data = struct.pack('?', False) + struct.pack('>I', len(message_data)) + message_data
        self._connection.send_data(self._stream_id, data, end_stream=False)
        self._writer.write(self._connection.data_to_send())

    async def drain(self):
        await self._writer.drain()

    def close_response(self, status_code=0, status_message=None):
        headers = [('grpc-status', str(status_code))]
        if status_message is not None:
            headers.append(('grpc-message', status_message))
        self._connection.send_headers(self._stream_id, headers, end_stream=True)
        self._writer.write(self._connection.data_to_send())


