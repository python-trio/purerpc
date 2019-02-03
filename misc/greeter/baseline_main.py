"""The Python implementation of the GRPC helloworld.Greeter server."""

from concurrent import futures
import time

import grpc

from generated.greeter_pb2 import HelloReply
from generated.greeter_pb2_grpc import GreeterServicer, add_GreeterServicer_to_server

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Greeter(GreeterServicer):

    def SayHelloToMany(self, request_iterator, context):
        requests = []
        for request in request_iterator:
            requests.append(request)

        name = requests[0].name
        for i in range(8):
            name += name
        yield HelloReply(message='Hello, {}'.format(name))


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    add_GreeterServicer_to_server(Greeter(), server)
    server.add_insecure_port('[::]:50055')
    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()

