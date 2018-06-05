import curio
import time
from purerpc.client import Channel, Stub
from greeter_pb2 import HelloRequest, HelloReply
from greeter_grpc import GreeterStub
from purerpc.utils import print_memory_growth_statistics


async def worker(channel):
    stub = GreeterStub(channel)
    for i in range(100):
        response = await stub.SayHello(HelloRequest(name="World"))
        assert(response.message == "Hello, World")


async def main_coro():
    # await curio.spawn(print_memory_growth_statistics(), daemon=True)
    channel = Channel("localhost", 50055)
    await channel.connect()
    for i in range(200):
        start = time.time()
        async with curio.TaskGroup() as task_group:
            for i in range(100):
                await task_group.spawn(worker(channel))
        print("RPS: {}".format(10000 / (time.time() - start)))


def main():
    curio.run(main_coro)


if __name__ == "__main__":
    main()
