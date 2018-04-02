import struct
import collections
from .exceptions import UnsupportedMessageEncodingError


class ByteBuffer:
    def __init__(self):
        self._deque = collections.deque()
        self._size = 0

    def append(self, data):
        if not isinstance(data, bytes):
            raise ValueError("Expected bytes")
        if data:
            self._deque.append(data)
            self._size += len(data)

    def popleft(self, amount):
        if amount > self._size:
            raise ValueError("Trying to extract {} bytes from ByteBuffer of length {}".format(
                amount, self._size))
        data = []
        while amount > 0:
            next_element = self._deque[0]
            if amount >= len(next_element):
                self._size -= len(next_element)
                amount -= len(next_element)
                data.append(self._deque.popleft())
            else:
                data.append(next_element[:amount])
                self._deque[0] = next_element[amount:]
                self._size -= amount
                amount = 0
        return b"".join(data)

    def __len__(self):
        return self._size


class MessageReadBuffer:
    def __init__(self, message_encoding=None):
        self._buffer = ByteBuffer()
        self._message_encoding = message_encoding
        self._compressed_flag = None
        self._message_length = None

    def data_received(self, data: bytes):
        self._buffer.append(data)

    def decompress(self, data):
        if self._message_encoding == "gzip" or self._message_encoding == "deflate":
            import zlib
            return zlib.decompress(data)
        elif self._message_encoding == "snappy":
            import snappy
            return snappy.decompress(data)
        else:
            raise UnsupportedMessageEncodingError(
                "Unsupported compression: {}".format(self._message_encoding))

    def read_one_message(self):
        # either compressed_flag = message_length = None and they are the next elements in
        # self._buffer, or they both not None, and the next element in self._buffer is data
        if self._message_length is None:
            if len(self._buffer) < 5:
                return None
            self._compressed_flag, self._message_length = struct.unpack('>?I',
                                                                        self._buffer.popleft(5))
        if len(self._buffer) < self._message_length:
            return None
        data = self._buffer.popleft(self._message_length)
        if self._compressed_flag:
            data = self.decompress(data)
        self._compressed_flag = self._message_length = None
        return data

    def read_all_complete_messages(self):
        messages = []
        while True:
            result = self.read_one_message()
            if result is not None:
                messages.append(result)
            else:
                break
        return messages


class MessageWriteBuffer:
    def __init__(self, message_encoding=None):
        self._buffer = ByteBuffer()
        self._message_encoding = message_encoding

    def compress(self, data):
        if self._message_encoding == "gzip" or self._message_encoding == "deflate":
            import zlib
            return zlib.compress(data)
        elif self._message_encoding == "snappy":
            import snappy
            return snappy.compress(data)
        else:
            raise UnsupportedMessageEncodingError(
                "Unsupported compression: {}".format(self._message_encoding))

    def write_message(self, data: bytes, compress=False):
        if compress:
            data = self.compress(data)
        self._buffer.append(struct.pack('>?I', compress, len(data)))
        self._buffer.append(data)

    def data_to_send(self, amount):
        return self._buffer.popleft(amount)

    def __len__(self):
        return len(self._buffer)
