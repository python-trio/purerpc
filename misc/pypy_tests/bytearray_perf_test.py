import collections


class ByteBuffer:
    def __init__(self, chunk_size=65536):
        self._deque = collections.deque([bytearray()])
        self._chunk_size = chunk_size
        self._size = 0

    def append(self, data):
        pos = 0
        while pos < len(data):
            data_to_write = min(self._chunk_size - len(self._deque[-1]), len(data) - pos)
            self._deque[-1].extend(data[pos:pos + data_to_write])
            if len(self._deque[-1]) == self._chunk_size:
                self._deque.append(bytearray())
            pos += data_to_write
            self._size += data_to_write

    def popleft(self, amount):
        if amount > self._size:
            raise ValueError("Trying to extract {} bytes from ByteBuffer of length {}".format(
                amount, self._size))
        data = bytearray()
        while amount > 0:
            data_to_read = min(amount, len(self._deque[0]))
            data.extend(self._deque[0][:data_to_read])
            self._deque[0] = self._deque[0][data_to_read:]
            if len(self._deque[0]) == 0 and len(self._deque) > 1:
                self._deque.popleft()
            amount -= data_to_read
            self._size -= data_to_read
        return bytes(data)

    def __len__(self):
        return self._size


class ByteBufferV2:
    def __init__(self):
        self._deque = collections.deque()
        self._size = 0

    def append(self, data):
        if not isinstance(data, bytes):
            raise ValueError("Expected bytes")
        if data:
            self._deque.append(data)
            self._size += len(data)

    def popleft_v2(self, amount):
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

    def popleft(self, amount):
        if amount > self._size:
            raise ValueError("Trying to extract {} bytes from ByteBuffer of length {}".format(
                amount, self._size))
        data = []
        while amount > 0:
            next_element = self._deque[0]
            bytes_to_read = min(amount, len(next_element))
            data.append(next_element[:bytes_to_read])
            self._deque[0] = next_element[bytes_to_read:]
            amount -= bytes_to_read
            self._size -= bytes_to_read
            if len(self._deque[0]) == 0:
                self._deque.popleft()
        return b"".join(data)

    def __len__(self):
        return self._size


def main():
    from purerpc.grpclib.buffers import ByteBuffer
    b = b"\x00" * 50
    x = ByteBuffer()
    for i in range(500000):
        for j in range(50):
            x.append(b)
        x.popleft(2000)


if __name__ == "__main__":
    main()
