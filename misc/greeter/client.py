import curio
import time
from purerpc.client import Channel, Stub
from greeter_pb2 import HelloRequest, HelloReply
from purerpc.utils import print_memory_growth_statistics


async def worker(channel):
    stub = Stub("Greeter", channel)
    for i in range(100):
        stream = await stub.rpc("SayHelloToMany", HelloRequest, HelloReply)
        await stream.send(HelloRequest(name="Hi, beyotch"))
        await stream.close()
        while True:
            msg = await stream.recv()
            if msg is None:
                break


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
