import anyio
import sys
import time
from generated import greeter_grpc, greeter_pb2
import purerpc


GreeterStub = greeter_grpc.GreeterStub



async def do_load_unary(result_queue, stub, num_requests, message_size):
    message = "0" * message_size
    start = time.time()
    for _ in range(num_requests):
        result = (await stub.SayHello(greeter_pb2.HelloRequest(name=message))).message
        assert (len(result) == message_size)
    avg_latency = (time.time() - start) / num_requests
    await result_queue.send(avg_latency)


async def do_load_stream(result_queue, stub, num_requests, message_size):
    message = "0" * message_size
    stream = await stub.SayHelloToMany()
    start = time.time()
    for _ in range(num_requests):
        await stream.send_message(greeter_pb2.HelloRequest(name=message))
        result = await stream.receive_message()
        assert (len(result.message) == message_size)
    avg_latency = (time.time() - start) / num_requests
    await stream.close()
    await stream.receive_message()
    await result_queue.send(avg_latency)


async def worker(port, num_concurrent_streams, num_requests_per_stream,
                 num_rounds, message_size, load_type):
    async with purerpc.insecure_channel("localhost", port) as channel:
        stub = GreeterStub(channel)
        if load_type == "unary":
            load_fn = do_load_unary
        elif load_type == "stream":
            load_fn = do_load_stream
        else:
            raise ValueError(f"Unknown load type: {load_type}")
        for idx in range(num_rounds):
            start = time.time()
            send_queue, receive_queue = anyio.create_memory_object_stream(max_buffer_size=sys.maxsize)
            async with anyio.create_task_group() as task_group:
                for _ in range(num_concurrent_streams):
                    task_group.start_soon(load_fn, send_queue, stub, num_requests_per_stream, message_size)
            end = time.time()

            rps = num_concurrent_streams * num_requests_per_stream / (end - start)

            latencies = []
            for _ in range(num_concurrent_streams):
                latencies.append(await receive_queue.receive())

            print("Round", idx, "rps", rps, "avg latency", 1000 * sum(latencies) / len(latencies))


if __name__ == "__main__":
    try:
        purerpc.run(worker, 50055, 100, 50, 10, 1000, "unary")
    except KeyboardInterrupt:
        pass
