import time
import curio
import argparse
import contextlib
import multiprocessing

import purerpc
from greeter_pb2 import HelloRequest, HelloReply
from greeter_grpc import GreeterServicer, GreeterStub


@contextlib.contextmanager
def run_purerpc_service_in_process(service):
    queue = multiprocessing.Queue()
    def target_fn():
        server = purerpc.Server(port=0)
        server.add_service(service)
        socket = server._create_socket_and_listen()
        queue.put(socket.getsockname()[1])
        queue.close()
        queue.join_thread()
        curio.run(server._run_async_server, socket)

    process = multiprocessing.Process(target=target_fn)
    process.start()
    port = queue.get()
    queue.close()
    queue.join_thread()
    try:
        yield port
    finally:
        process.terminate()
        process.join()


class Greeter(GreeterServicer):
    async def SayHello(self, message):
        return HelloReply(message=message.name)

    async def SayHelloToMany(self, input_messages):
        async for message in input_messages:
            yield HelloReply(message=message.name)


async def do_load_unary(stub, num_requests, message_size):
    message = "0" * message_size
    start = time.time()
    for _ in range(num_requests):
        result = (await stub.SayHello(HelloRequest(name=message))).message
        assert (len(result) == message_size)
    avg_latency = (time.time() - start) / num_requests
    return avg_latency


async def do_load_stream(stub, num_requests, message_size):
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
    return avg_latency


async def worker(port, queue, num_concurrent_streams, num_requests_per_stream,
                 num_rounds, message_size, load_type):
    channel = purerpc.Channel("localhost", port)
    await channel.connect()
    stub = GreeterStub(channel)
    if load_type == "unary":
        load_fn = do_load_unary
    elif load_type == "stream":
        load_fn = do_load_stream
    else:
        raise ValueError(f"Unknown load type: {load_type}")
    for _ in range(num_rounds):
        tasks = []
        start = time.time()
        async with curio.TaskGroup() as task_group:
            for _ in range(num_concurrent_streams):
                task = await task_group.spawn(load_fn(stub, num_requests_per_stream, message_size))
                tasks.append(task)
        end = time.time()
        rps = num_concurrent_streams * num_requests_per_stream / (end - start)
        queue.put(rps)
        queue.put([task.result for task in tasks])
    queue.close()
    queue.join_thread()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--message_size", type=int, default=1000)
    parser.add_argument("--num_workers", type=int, default=3)
    parser.add_argument("--num_concurrent_streams", type=int, default=100)
    parser.add_argument("--num_requests_per_stream", type=int, default=100)
    parser.add_argument("--num_rounds", type=int, default=10)
    parser.add_argument("--load_type", choices=["unary", "stream"], required=True)

    args = parser.parse_args()

    queues = [multiprocessing.Queue() for _ in range(args.num_workers)]

    with run_purerpc_service_in_process(Greeter().service) as port:
        def target_fn(worker_id):
            queue = queues[worker_id]
            curio.run(worker, port, queue, args.num_concurrent_streams,
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
