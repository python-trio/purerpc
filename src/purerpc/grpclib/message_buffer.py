import struct
from .exceptions import UnsupportedMessageEncodingError


class MessageBuffer:
    def __init__(self, message_encoding=None):
        self._buffer = bytearray()
        self._message_encoding = message_encoding

    def write(self, data: bytes):
        self._buffer.extend(data)

    def read(self):
        data = bytes(self._buffer)
        self._buffer = bytearray()
        return data

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

    def read_all_complete_messages(self):
        pos = 0
        messages = []
        while True:
            if pos + 5 > len(self._buffer):
                break
            compressed_flag, message_length = struct.unpack('>?I', self._buffer[pos:pos + 5])
            if pos + 5 + message_length > len(self._buffer):
                self._buffer = self._buffer[pos:]
                break
            else:
                pos += 5
                data = bytes(self._buffer[pos:pos + message_length])
                pos += message_length
                if compressed_flag:
                    data = self.decompress(data)
                messages.append(data)
        return messages

    def write_complete_message(self, data: bytes, compress=False):
        if compress:
            data = self.compress(data)
        self.write(struct.pack('>?I', compress, len(data)) + data)
