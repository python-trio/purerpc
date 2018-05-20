import logging
import logging.config

import curio

from purerpc.server import Service, Server, Stream
from greeter_pb2 import HelloRequest, HelloReply
from greeter_grpc import GreeterServicer
from async_generator import async_generator, yield_


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


class Greeter(GreeterServicer):
    @async_generator
    async def SayHelloToMany(self, input_messages):
        await yield_(HelloReply(message="Hello, world!"))


server = Server(50055)
server.add_service(Greeter().service)

if __name__ == "__main__":
    server.serve()
