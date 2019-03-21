from async_generator import async_generator, yield_
from generated import greeter_grpc, greeter_pb2

import purerpc


GreeterServicer = greeter_grpc.GreeterServicer
class Servicer(GreeterServicer):
    async def SayHello(self, message):
        return greeter_pb2.HelloReply(message=message.name)

    @async_generator
    async def SayHelloGoodbye(self, message):
        await yield_(greeter_pb2.HelloReply(message=message.name))
        await yield_(greeter_pb2.HelloReply(message=message.name))

    async def SayHelloToManyAtOnce(self, messages):
        names = []
        async for message in messages:
            names.append(message.name)
        return greeter_pb2.HelloReply(message="".join(names))

    @async_generator
    async def SayHelloToMany(self, messages):
        async for message in messages:
            await yield_(greeter_pb2.HelloReply(message=message.name))


def main():
    server = purerpc.Server(50055, num_processes=1)
    server.add_service(Servicer().service)
    server.serve()


if __name__ == "__main__":
    main()
