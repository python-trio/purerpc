import time
import anyio
import sys
import argparse
import multiprocessing

import purerpc
from generated.greeter_pb2 import HelloRequest, HelloReply
from generated.greeter_grpc import GreeterServicer, GreeterStub

from purerpc.test_utils import run_purerpc_service_in_process


class Greeter(GreeterServicer):
    async def SayHello(self, message):
        return HelloReply(message=message.name)

    async def SayHelloToMany(self, input_messages):
        async for message in input_messages:
            yield HelloReply(message=message.name)


async def do_load_unary(result_queue, stub, num_requests, message_size):
    message = "0" * message_size
    start = time.time()
    for _ in range(num_requests):
        result = (await stub.SayHello(HelloRequest(name=message))).message
        assert (len(result) == message_size)
    avg_latency = (time.time() - start) / num_requests
    await result_queue.send(avg_latency)


async def do_load_stream(result_queue, stub, num_requests, message_size):
    message = "0" * message_size
    stream = await stub.SayHelloToMany()
    start = time.time()
    for _ in range(num_requests):
        await stream.send_message(HelloRequest(name=message))
        result = await stream.receive_message()
        assert (len(result.message) == message_size)
    avg_latency = (time.time() - start) / num_requests
    await stream.close()
    await stream.receive_message()
    await result_queue.send(avg_latency)


async def worker(port, queue, num_concurrent_streams, num_requests_per_stream,
                 num_rounds, message_size, load_type):
    async with purerpc.insecure_channel("localhost", port) as channel:
        stub = GreeterStub(channel)
        if load_type == "unary":
            load_fn = do_load_unary
        elif load_type == "stream":
            load_fn = do_load_stream
        else:
            raise ValueError(f"Unknown load type: {load_type}")
        for _ in range(num_rounds):
            start = time.time()
            send_queue, receive_queue = anyio.create_memory_object_stream(max_buffer_size=sys.maxsize)
            async with anyio.create_task_group() as task_group:
                for _ in range(num_concurrent_streams):
                    task_group.start_soon(load_fn, send_queue, stub, num_requests_per_stream, message_size)
            end = time.time()
            rps = num_concurrent_streams * num_requests_per_stream / (end - start)
            queue.put(rps)
            results = []
            for _ in range(num_concurrent_streams):
                results.append(await receive_queue.receive())
            queue.put(results)
        queue.close()
        queue.join_thread()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message_size", type=int, default=1000)
    parser.add_argument("--num_workers", type=int, default=3)
    parser.add_argument("--num_concurrent_streams", type=int, default=100)
    parser.add_argument("--num_requests_per_stream", type=int, default=50)
    parser.add_argument("--num_rounds", type=int, default=10)
    parser.add_argument("--load_type", choices=["unary", "stream"], required=True)

    args = parser.parse_args()

    queues = [multiprocessing.Queue() for _ in range(args.num_workers)]

    with run_purerpc_service_in_process(Greeter().service) as port:
        def target_fn(worker_id):
            queue = queues[worker_id]
            purerpc.run(worker, port, queue, args.num_concurrent_streams,
                        args.num_requests_per_stream, args.num_rounds, args.message_size,
                        args.load_type)

        processes = []
        for worker_id in range(args.num_workers):
            process = multiprocessing.Process(target=target_fn, args=(worker_id,))
            process.start()
            processes.append(process)

        for round_id in range(args.num_rounds):
            total_rps = 0
            latencies = []
            for queue in queues:
                total_rps += queue.get()
                latencies.extend(queue.get())
            avg_latency = 1000 * sum(latencies) / len(latencies)
            max_latency = 1000 * max(latencies)
            print(f"Round {round_id}, RPS: {total_rps}, avg latency: {avg_latency} ms, "
                  f"max latency: {max_latency} ms")

        for queue in queues:
            queue.close()
            queue.join_thread()

        for process in processes:
            process.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
