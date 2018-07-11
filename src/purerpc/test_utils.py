import unittest
import threading
import multiprocessing
import curio
import subprocess
import purerpc
import tempfile
import shutil
import os
import sys
import inspect
import importlib
import concurrent.futures
import logging
import logging.config
import contextlib
import time
import random
import string


class PureRPCTestCase(unittest.TestCase):
    def random_payload(self, min_size=1000, max_size=100000):
        return "".join(random.choice(string.ascii_letters)
                       for _ in range(random.randint(min_size, max_size)))

    @contextlib.contextmanager
    def run_purerpc_service_in_process(self, service):
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

    @contextlib.contextmanager
    def run_grpc_service_in_process(self, add_handler_fn):
        queue = multiprocessing.Queue()
        def target_fn():
            import grpc
            server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=8))
            port = server.add_insecure_port('[::]:0')
            add_handler_fn(server)
            server.start()

            queue.put(port)
            queue.close()
            queue.join_thread()
            while True:
                time.sleep(60)

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

    def run_tests_in_workers(self, *, target, num_workers):
        queue = multiprocessing.Queue()

        def target_fn():
            try:
                target()
            except:
                queue.put(False)
                raise
            else:
                queue.put(True)
            queue.close()
            queue.join_thread()

        processes = []
        for _ in range(num_workers):
            process = multiprocessing.Process(target=target_fn)
            process.start()
            processes.append(process)

        for _ in range(num_workers):
            self.assertTrue(queue.get())
        queue.close()
        queue.join_thread()

        for process in processes:
            process.join()

    @contextlib.contextmanager
    def compile_temp_proto(self, *relative_proto_paths):
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
                               '--purerpc_out=.', f'-I{temp_dir}', proto_temp_path]
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

    def configure_logs(self):
        conf = {
            "version": 1,
            "formatters": {
                "simple": {
                    "format": "[%(asctime)s - %(name)s - %(levelname)s]:  %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "level": "DEBUG",
                "handlers": ["console"],
            },
            "disable_existing_loggers": False
        }
        logging.config.dictConfig(conf)
