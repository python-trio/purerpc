import unittest
import threading
import multiprocessing
import curio
import subprocess
import purerpc
import tempfile
import shutil
import grpc
import os
import sys
import importlib
import concurrent.futures
import logging
import logging.config
import contextlib
import time


class PureRPCTestCase(unittest.TestCase):
    @contextlib.contextmanager
    def run_purerpc_service_in_process(self, service):
        queue = multiprocessing.Queue()
        def target_fn():
            server = purerpc.Server(port=0)
            server.add_service(service)
            socket = server._create_socket_and_listen()
            queue.put(socket.getsockname()[1])
            curio.run(server._run_async_server, socket)

        process = multiprocessing.Process(target=target_fn)
        process.start()
        port = queue.get()
        try:
            yield port
        finally:
            process.terminate()
            process.join()

    @contextlib.contextmanager
    def run_grpc_service_in_process(self, add_handler_fn):
        queue = multiprocessing.Queue()
        def target_fn():
            server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=8))
            port = server.add_insecure_port('[::]:0')
            add_handler_fn(server)
            server.start()

            queue.put(port)
            while True:
                time.sleep(60)

        process = multiprocessing.Process(target=target_fn)
        process.start()
        port = queue.get()
        try:
            yield port
        finally:
            process.terminate()
            process.join()

    @contextlib.contextmanager
    def compile_temp_proto(self, proto_path):
        with tempfile.TemporaryDirectory() as temp_dir:
            proto_filename = os.path.basename(proto_path)
            proto_temp_path = os.path.join(temp_dir, proto_filename)
            shutil.copyfile(proto_path, proto_temp_path)
            cmdline = [sys.executable, '-m', 'grpc_tools.protoc', '--python_out=.',
                       '--purerpc_out=.', f'-I{temp_dir}', proto_temp_path]
            subprocess.check_call(cmdline, cwd=temp_dir)
            sys.path.insert(0, temp_dir)
            pb2_module_name = proto_filename.replace(".proto", "_pb2")
            grpc_module_name = proto_filename.replace(".proto", "_grpc")
            try:
                pb2_module = importlib.import_module(pb2_module_name)
                grpc_module = importlib.import_module(grpc_module_name)
                yield pb2_module, grpc_module
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
