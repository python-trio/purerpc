import unittest
import curio
import grpc
import typing
import time
import logging
import logging.config
import threading
from .greeter_pb2 import HelloReply, HelloRequest, GreeterStub
from async_generator import async_generator, yield_
from purerpc.server import Service


def configure_logs(log_file=None):
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
    if log_file is not None:
        conf["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": log_file,
        }
        conf["root"]["handlers"].append("file")
    logging.config.dictConfig(conf)


configure_logs()


class TestServer(unittest.TestCase):
    def setUp(self):
        pass

    def run_server(self, port):
        service = Service(port)

        @service.rpc("SayHelloToMany", HelloRequest)
        @async_generator
        async def say_hello_to_many(message_reader):
            async for message in message_reader:
                await curio.sleep(0.05)
                await yield_(HelloReply(message="Hello " + message.name))

        async def main():
            await curio.ignore_after(10, service)

        curio.run(main)

    def test_server(self):
        thread = threading.Thread(target=self.run_server, args=(42419,))
        thread.start()
        try:
            time.sleep(1.0)

            def name_generator():
                names = ('Foo', 'Bar', 'Bat', 'Baz')
                for name in names:
                    yield HelloRequest(name=name)

            channel = grpc.insecure_channel('127.0.0.1:42419')
            print("Opening channel")
            stub = GreeterStub(channel)
            print("Started")
            response_iterator = stub.SayHelloToMany(name_generator())
            responses = []
            for response in response_iterator:
                responses.append(response.message)
                print(responses)
            print("Done")

            self.assertEqual(responses, ["Hello Foo", "Hello Bar", "Hello Bat", "Hello Baz"])
        finally:
            thread.join()
