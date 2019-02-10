import unittest
import functools
import collections
import subprocess
import multiprocessing
import tempfile
import shutil
import os
import sys
import inspect
import importlib
import concurrent.futures
import logging
import contextlib
import time
import random
import string
from queue import Empty as QueueEmpty

from tblib import pickling_support
pickling_support.install()

import anyio
from async_generator import aclosing


WrappedResult = collections.namedtuple("WrappedResult", ("result", "exc_info"))


def wrap_gen_in_process(queue):
    def decorator(gen):
        @functools.wraps(gen)
        def new_func(*args, **kwargs):
            try:
                for elem in gen(*args, **kwargs):
                    queue.put(WrappedResult(result=elem, exc_info=None))
            except:
                queue.put(WrappedResult(result=None, exc_info=sys.exc_info()))
            finally:
                queue.close()
                queue.join_thread()
        return new_func
    return decorator


class PureRPCTestCase(unittest.TestCase):
    @staticmethod
    async def async_iterable_to_list(async_iterable):
        result = []
        async with aclosing(async_iterable) as async_iterable:
            async for value in async_iterable:
                result.append(value)
        return result

    @staticmethod
    def random_payload(min_size=1000, max_size=100000):
        return "".join(random.choice(string.ascii_letters)
                       for _ in range(random.randint(min_size, max_size)))

    @staticmethod
    @contextlib.contextmanager
    def run_context_manager_generator_in_process(cm_gen):
        queue = multiprocessing.Queue()
        target_fn = wrap_gen_in_process(queue)(cm_gen)

        process = multiprocessing.Process(target=target_fn)
        process.start()
        try:
            wrapped_result = queue.get()
            if wrapped_result.exc_info is not None:
                raise wrapped_result.exc_info[0].with_traceback(*wrapped_result.exc_info[1:])
            else:
                yield wrapped_result.result
        finally:
            try:
                exc_info = queue.get_nowait().exc_info
                if exc_info is not None:
                    raise exc_info[0].with_traceback(*exc_info[1:])
            except QueueEmpty:
                pass
            finally:
                process.terminate()
                process.join()
                queue.close()
                queue.join_thread()

    @classmethod
    def run_purerpc_service_in_process(self, service):
        def target_fn():
            import purerpc
            server = purerpc.Server(port=0)
            server.add_service(service)
            socket = server._create_socket_and_listen()
            yield socket.getsockname()[1]
            anyio.run(server._run_async_server, socket)
        return self.run_context_manager_generator_in_process(target_fn)

    @classmethod
    def run_grpc_service_in_process(self, add_handler_fn):
        def target_fn():
            import grpc
            server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=8))
            port = server.add_insecure_port('[::]:0')
            add_handler_fn(server)
            server.start()
            yield port
            while True:
                time.sleep(60)
        return self.run_context_manager_generator_in_process(target_fn)

    @staticmethod
    def run_tests_in_workers(*, target, num_workers):
        queue = multiprocessing.Queue()

        @wrap_gen_in_process(queue)
        def target_fn():
            target()
            yield

        processes = [multiprocessing.Process(target=target_fn) for _ in range(num_workers)]
        for process in processes:
            process.start()

        try:
            for _ in range(num_workers):
                wrapped_result = queue.get()
                if wrapped_result.exc_info is not None:
                    raise wrapped_result.exc_info[0].with_traceback(*wrapped_result.exc_info[1:])
        finally:
            queue.close()
            queue.join_thread()
            for process in processes:
                process.join()

    @staticmethod
    @contextlib.contextmanager
    def compile_temp_proto(*relative_proto_paths):
        modules = []
        with tempfile.TemporaryDirectory() as temp_dir:
            sys.path.insert(0, temp_dir)
            try:
                for relative_proto_path in relative_proto_paths:
                    proto_path = os.path.join(os.path.dirname(
                        inspect.currentframe().f_back.f_back.f_globals['__file__']),
                        relative_proto_path)
                    proto_filename = os.path.basename(proto_path)
                    proto_temp_path = os.path.join(temp_dir, proto_filename)
                    shutil.copyfile(proto_path, proto_temp_path)
                for relative_proto_path in relative_proto_paths:
                    proto_filename = os.path.basename(relative_proto_path)
                    proto_temp_path = os.path.join(temp_dir, proto_filename)
                    cmdline = [sys.executable, '-m', 'grpc_tools.protoc', '--python_out=.',
                               '--purerpc_out=.', '-I' + temp_dir, proto_temp_path]
                    subprocess.check_call(cmdline, cwd=temp_dir)
                    pb2_module_name = proto_filename.replace(".proto", "_pb2")
                    grpc_module_name = proto_filename.replace(".proto", "_grpc")
                    pb2_module = importlib.import_module(pb2_module_name)
                    grpc_module = importlib.import_module(grpc_module_name)
                    modules.extend((pb2_module, grpc_module))
                yield modules
            finally:
                sys.path.remove(temp_dir)

    def setUp(self):
        self.configure_logs()

    @staticmethod
    def configure_logs():
        logging.basicConfig(format="[%(asctime)s - %(name)s - %(levelname)s]:  %(message)s", level=logging.WARNING)
