# from gevent import monkey
# monkey.patch_all()
#
# import grpc._cython.cygrpc
# grpc._cython.cygrpc.init_grpc_gevent()


import time
import argparse
import functools
from queue import Queue
import multiprocessing




import grpc
from generated.greeter_pb2 import HelloRequest, HelloReply
from generated.greeter_pb2_grpc import GreeterServicer, GreeterStub, add_GreeterServicer_to_server

from purerpc.test_utils import run_grpc_service_in_process


class Greeter(GreeterServicer):
    def SayHello(self, message, context):
        return HelloReply(message=message.name[::-1])

    def SayHelloToMany(self, messages, context):
        for message in messages:
            yield HelloReply(message=message.name[::-1])


def do_load_unary(result_queue, stub, num_requests, message_size):
    requests_left = num_requests
    avg_latency = 0
    message = "0" * message_size
    start = time.time()
    fut = stub.SayHello.future(HelloRequest(name=message))

    def done_callback(fut):
        nonlocal requests_left
        nonlocal avg_latency
        requests_left -= 1
        assert len(fut.result().message) == message_size
        if requests_left > 0:
            fut = stub.SayHello.future(HelloRequest(name=message))
            fut.add_done_callback(done_callback)
        else:
            avg_latency = (time.time() - start) / num_requests
            result_queue.put(avg_latency)

    fut.add_done_callback(done_callback)


# def do_load_stream(result_queue, stub, num_requests, message_size):
#     message = "0" * message_size
#     stream = await stub.SayHelloToMany()
#     start = time.time()
#     for _ in range(num_requests):
#         await stream.send_message(HelloRequest(name=message))
#         result = await stream.receive_message()
#         assert (len(result.message) == message_size)
#     avg_latency = (time.time() - start) / num_requests
#     await stream.close()
#     await stream.receive_message()
#     await result_queue.put(avg_latency)


def worker(port, queue, num_concurrent_streams, num_requests_per_stream,
           num_rounds, message_size, load_type):
    with grpc.insecure_channel("localhost:{}".format(port)) as channel:
        stub = GreeterStub(channel)
        if load_type == "unary":
            load_fn = do_load_unary
        else:
            raise ValueError(f"Unknown load type: {load_type}")
        for _ in range(num_rounds):
            start = time.time()
            task_results = Queue()
            for _ in range(num_concurrent_streams):
                load_fn(task_results, stub, num_requests_per_stream, message_size)

            results = []
            for _ in range(num_concurrent_streams):
                results.append(task_results.get())

            end = time.time()
            rps = num_concurrent_streams * num_requests_per_stream / (end - start)
            queue.put(rps)
            queue.put(results)
        queue.close()
        queue.join_thread()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--message_size", type=int, default=1000)
    parser.add_argument("--num_workers", type=int, default=3)
    parser.add_argument("--num_concurrent_streams", type=int, default=100)
    parser.add_argument("--num_requests_per_stream", type=int, default=50)
    parser.add_argument("--num_rounds", type=int, default=10)
    parser.add_argument("--load_type", choices=["unary", "stream"], required=True)

    args = parser.parse_args()

    queues = [multiprocessing.Queue() for _ in range(args.num_workers)]

    with run_grpc_service_in_process(functools.partial(add_GreeterServicer_to_server, Greeter())) as port:
        def target_fn(worker_id):
            queue = queues[worker_id]
            worker(port, queue, args.num_concurrent_streams,
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
