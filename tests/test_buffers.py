import zlib
import unittest
import random
import struct
from purerpc.grpclib.buffers import ByteBuffer, MessageReadBuffer


class TestByteBuffer(unittest.TestCase):
    def test_byte_buffer_random(self):
        byte_buffer = ByteBuffer()
        byte_array = bytearray()
        for i in range(1000):
            data = bytes(random.randint(0, 255) for _ in range(random.randint(0, 100)))
            byte_buffer.append(data)
            byte_array.extend(data)
            self.assertEqual(len(byte_buffer), len(byte_array))
            num_elements = min(random.randint(0, 100), len(byte_buffer))
            self.assertEqual(byte_array[:num_elements], byte_buffer.popleft(num_elements))
            byte_array = byte_array[num_elements:]

    def test_byte_buffer_large_reads(self):
        byte_buffer = ByteBuffer()
        byte_array = bytearray()
        for i in range(1000):
            for j in range(100):
                data = bytes([(i + j) % 256])
                byte_buffer.append(data)
                byte_array.extend(data)
            self.assertEqual(len(byte_array), len(byte_buffer))
            num_elements = min(random.randint(0, 100), len(byte_buffer))
            self.assertEqual(byte_array[:num_elements], byte_buffer.popleft(num_elements))
            byte_array = byte_array[num_elements:]

    def test_byte_buffer_large_writes(self):
        byte_buffer = ByteBuffer()
        byte_array = bytearray()
        data = bytes(range(256)) * 10
        for i in range(250):
            byte_buffer.append(data)
            byte_array.extend(data)
            for j in range(10):
                self.assertEqual(len(byte_array), len(byte_buffer))
                num_elements = min(random.randint(0, 100), len(byte_buffer))
                self.assertEqual(byte_array[:num_elements], byte_buffer.popleft(num_elements))
                byte_array = byte_array[num_elements:]


class TestMessageReadBuffer(unittest.TestCase):
    def test_message_read_buffer(self):
        buffer = bytearray()
        for i in range(100):
            data = bytes(range(i))
            compress_flag = False
            if i % 2:
                data = zlib.compress(data)
                compress_flag = True
            buffer.extend(struct.pack('>?I', compress_flag, len(data)))
            buffer.extend(data)

        read_buffer = MessageReadBuffer(message_encoding="gzip")
        messages = []
        while buffer:
            if random.choice([True, False]):
                num_bytes = random.randint(0, 50)
                read_buffer.data_received(bytes(buffer[:num_bytes]))
                buffer = buffer[num_bytes:]
            else:
                messages.extend(read_buffer.read_all_complete_messages())
        messages.extend(read_buffer.read_all_complete_messages())

        self.assertEqual(len(messages), 100)
        for idx, message in enumerate(messages):
            self.assertEqual(message, bytes(range(idx)))

