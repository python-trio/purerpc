import time

import anyio

import purerpc
from generated.greeter_pb2 import HelloRequest
from generated.greeter_grpc import GreeterStub


async def worker(channel):
    stub = GreeterStub(channel)
    for i in range(100):
        data = "World" * 1
        response = await stub.SayHello(HelloRequest(name=data))
        assert(response.message == "Hello, " + data)


async def main_coro():
    async with purerpc.insecure_channel("localhost", 50055) as channel:
        for _ in range(100):
            start = time.time()
            async with anyio.create_task_group() as task_group:
                for _ in range(100):
                    task_group.start_soon(worker, channel)
            print("RPS: {}".format(10000 / (time.time() - start)))


def main():
    purerpc.run(main_coro)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
