import logging
import logging.config

import curio

from purerpc.curio_service import Service
from greeter_pb2 import HelloRequest, HelloReply
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


service = Service(50055)


@service.rpc("SayHelloToMany", HelloRequest)
@async_generator
async def say_hello_to_many(message_iterator):
    await yield_(HelloReply(message="Hello world"))


if __name__ == "__main__":
    curio.run(service)
