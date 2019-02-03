import logging
import logging.config

from purerpc.server import Service, Server
from purerpc.rpc import Stream
from generated.greeter_pb2 import HelloRequest, HelloReply


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


service = Service("Greeter")


@service.rpc("SayHelloToMany")
async def say_hello_to_many(message: Stream[HelloRequest]) -> Stream[HelloReply]:
    yield HelloReply(message="Hello, world!")

server = Server(50055)
server.add_service(service)

if __name__ == "__main__":
    server.serve()
