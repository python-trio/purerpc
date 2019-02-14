import anyio

from async_generator import async_generator, yield_
from generated import greeter_grpc, greeter_pb2
import purerpc
from purerpc.test_utils import random_payload


GreeterStub = greeter_grpc.GreeterStub


async def worker(channel):
    stub = GreeterStub(channel)
    data = random_payload()

    @async_generator
    async def gen():
        for _ in range(4):
            await yield_(greeter_pb2.HelloRequest(name=data))


    print("stream_unary")
    assert (await stub.SayHelloToManyAtOnce(gen())).message == data * 4
    print("Done")


async def main():
    async with purerpc.insecure_channel("localhost", 50055) as channel:
        async with anyio.create_task_group() as task_group:
            for _ in range(20):
                await task_group.spawn(worker, channel)


if __name__ == "__main__":
    for i in range(50):
        anyio.run(main)
