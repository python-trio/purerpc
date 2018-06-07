import unittest
import threading
import multiprocessing
import curio
import purerpc
import grpc
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
