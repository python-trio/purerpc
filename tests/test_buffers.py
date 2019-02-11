import zlib
import random
import struct

import pytest

from purerpc.grpclib.buffers import ByteBuffer, MessageReadBuffer

byte_buffer = pytest.fixture(lambda: ByteBuffer())
byte_array = pytest.fixture(lambda: bytearray())


def test_byte_buffer_random(byte_buffer, byte_array):
    for i in range(1000):
        data = bytes(random.randint(0, 255) for _ in range(random.randint(0, 100)))
        byte_buffer.append(data)
        byte_array.extend(data)
        assert len(byte_buffer) == len(byte_array)
        num_elements = min(random.randint(0, 100), len(byte_buffer))
        assert byte_array[:num_elements] == byte_buffer.popleft(num_elements)
        byte_array = byte_array[num_elements:]


def test_byte_buffer_large_reads(byte_buffer, byte_array):
    for i in range(1000):
        for j in range(100):
            data = bytes([(i + j) % 256])
            byte_buffer.append(data)
            byte_array.extend(data)
        assert len(byte_array) == len(byte_buffer)
        num_elements = min(random.randint(0, 100), len(byte_buffer))
        assert byte_array[:num_elements] == byte_buffer.popleft(num_elements)
        byte_array = byte_array[num_elements:]


def test_byte_buffer_large_writes(byte_buffer, byte_array):
    data = bytes(range(256)) * 10
    for i in range(250):
        byte_buffer.append(data)
        byte_array.extend(data)
        for j in range(10):
            assert len(byte_array) == len(byte_buffer)
            num_elements = min(random.randint(0, 100), len(byte_buffer))
            assert byte_array[:num_elements] == byte_buffer.popleft(num_elements)
            byte_array = byte_array[num_elements:]


def test_message_read_buffer(byte_array):
    for i in range(100):
        data = bytes(range(i))
        compress_flag = False
        if i % 2:
            data = zlib.compress(data)
            compress_flag = True
        byte_array.extend(struct.pack('>?I', compress_flag, len(data)))
        byte_array.extend(data)

    read_buffer = MessageReadBuffer(message_encoding="gzip")
    messages = []
    while byte_array:
        if random.choice([True, False]):
            num_bytes = random.randint(0, 50)
            read_buffer.data_received(bytes(byte_array[:num_bytes]))
            byte_array = byte_array[num_bytes:]
        else:
            messages.extend(read_buffer.read_all_complete_messages())
    messages.extend(read_buffer.read_all_complete_messages())

    assert len(messages) == 100
    for idx, message in enumerate(messages):
        assert message == bytes(range(idx))
