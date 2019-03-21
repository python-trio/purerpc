import struct
import collections
from .exceptions import UnsupportedMessageEncodingError, MessageTooLargeError


class ByteBuffer:
    def __init__(self):
        self._deque = collections.deque()
        self._size = 0
        self._flow_controlled_length = 0

    def append(self, data, flow_controlled_length=None):
        if not isinstance(data, bytes) and not isinstance(data, bytearray):
            raise ValueError("Expected bytes")
        if flow_controlled_length is None:
            flow_controlled_length = len(data)
        if flow_controlled_length < len(data):
            raise ValueError("flow_controlled_length should be >= len(data)")
        self._deque.append((data, flow_controlled_length))
        self._size += len(data)

    def popleft_flowcontrol(self, amount):
        if amount > self._size:
            raise ValueError("Trying to extract {} bytes from ByteBuffer of length {}".format(
                amount, self._size))
        data = []
        flow_controlled_length = 0
        while amount > 0:
            next_element = self._deque[0][0]
            next_element_flow_controlled_length = self._deque[0][1]
            if amount >= len(next_element):
                self._size -= len(next_element)
                self._flow_controlled_length -= next_element_flow_controlled_length
                amount -= len(next_element)
                flow_controlled_length += next_element_flow_controlled_length
                data.append(next_element)
                self._deque.popleft()
            else:
                data.append(next_element[:amount])
                self._deque[0] = (next_element[amount:],
                                  next_element_flow_controlled_length - amount)
                self._size -= amount
                self._flow_controlled_length -= amount
                flow_controlled_length += amount
                amount = 0
        return b"".join(data), flow_controlled_length

    def popleft(self, amount):
        return self.popleft_flowcontrol(amount)[0]

    def __len__(self):
        return self._size

    @property
    def flow_controlled_length(self):
        return self._flow_controlled_length

    @property
    def length(self):
        return len(self)


class MessageReadBuffer:
    def __init__(self, message_encoding=None, max_message_length=4*1024*1024):
        self._message_encoding = message_encoding
        self._max_message_length = max_message_length

        self._buffer = ByteBuffer()
        self._messages = collections.deque()

        # MessageReadBuffer parser state
        self._compressed_flag = None
        self._message_length = None
        self._flow_controlled_length = None

    def data_received(self, data: bytes, flow_controlled_length=None):
        self._buffer.append(data, flow_controlled_length)
        self._process_new_messages()

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

    def _parse_one_message(self):
        # either compressed_flag = message_length = flow_controlled_length = None and
        # compressed_flag, message_length are the next elements in self._buffer, or they are all
        # not None, and the next element in self._buffer is data
        if self._message_length is None:
            if len(self._buffer) < 5:
                return None, 0
            message_header, self._flow_controlled_length = self._buffer.popleft_flowcontrol(5)
            self._compressed_flag, self._message_length = struct.unpack('>?I', message_header)
            if self._message_length > self._max_message_length:
                # Even after the error is raised, the state is not corrupted, and parsing
                # can be safely resumed
                raise MessageTooLargeError(
                    "Received message larger than max: {message_length} > {max_message_length}".format(
                        message_length=self._message_length,
                        max_message_length=self._max_message_length,
                    )
                )
        if len(self._buffer) < self._message_length:
            return None, 0
        data, flow_controlled_length = self._buffer.popleft_flowcontrol(self._message_length)
        flow_controlled_length += self._flow_controlled_length
        if self._compressed_flag:
            data = self.decompress(data)
        self._compressed_flag = self._message_length = self._flow_controlled_length = None
        return data, flow_controlled_length

    def _process_new_messages(self):
        while True:
            result, flow_controlled_length = self._parse_one_message()
            if result is not None:
                self._messages.append((result, flow_controlled_length))
            else:
                return

    def __len__(self):
        return len(self._messages)

    def read_all_complete_messages(self):
        messages = [message for message, _ in self._messages]
        self._messages = collections.deque()
        return messages

    def read_all_complete_messages_flowcontrol(self):
        messages = self._messages
        self._messages = collections.deque()
        return messages

    def read_message(self):
        return self._messages.popleft()[0]

    def read_message_flowcontrol(self):
        return self._messages.popleft()


class MessageWriteBuffer:
    def __init__(self, message_encoding=None, max_message_length=4*1024*1024):
        self._buffer = ByteBuffer()
        self._message_encoding = message_encoding
        self._max_message_length = max_message_length

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
        if len(data) > self._max_message_length:
            raise MessageTooLargeError(
                "Trying to send message larger than max: {message_length} > {max_message_length}".format(
                    message_length=len(data),
                    max_message_length=self._max_message_length,
                )
            )
        self._buffer.append(struct.pack('>?I', compress, len(data)))
        self._buffer.append(data)

    def data_to_send(self, amount):
        return self._buffer.popleft(amount)

    def __len__(self):
        return len(self._buffer)
