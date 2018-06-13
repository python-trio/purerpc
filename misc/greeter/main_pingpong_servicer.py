import argparse
import multiprocessing
import logging
import logging.config

import curio

from purerpc.server import Service, Server
from purerpc.rpc import Stream
from greeter_pb2 import HelloRequest, HelloReply
from greeter_grpc import GreeterServicer

"""
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
                "level": "WARNING",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "level": "WARNING",
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
"""


class Greeter(GreeterServicer):
    async def SayHello(self, message):
        return HelloReply(message="Hello, " + message.name)

    async def SayHelloToMany(self, input_messages):
        async for _ in input_messages:
            pass
        yield HelloReply(message="Hello, world!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_processes", default=0, type=int)
    args = parser.parse_args()

    if args.num_processes == 0:
        num_processes = multiprocessing.cpu_count()
    else:
        num_processes = args.num_processes

    server = Server(50055, num_processes=num_processes)
    server.add_service(Greeter().service)
    server.serve()
