import purerpc.server
from async_generator import async_generator
import greeter_pb2


class GreeterServicer(purerpc.server.Servicer):
    async def SayHello(self, input_message):
        raise NotImplementedError()

    @async_generator
    async def SayHelloGoodbye(self, input_message):
        raise NotImplementedError()

    @async_generator
    async def SayHelloToMany(self, input_messages):
        raise NotImplementedError()

    async def SayHelloToManyAtOnce(self, input_messages):
        raise NotImplementedError()

    @property
    def service(self) -> purerpc.server.Service:
        service_obj = purerpc.server.Service("Greeter")
        service_obj.add_unary_unary("SayHello", self.SayHello,
                                    greeter_pb2.HelloRequest, greeter_pb2.HelloReply)
        service_obj.add_unary_stream("SayHelloGoodbye", self.SayHelloGoodbye,
                                     greeter_pb2.HelloRequest, greeter_pb2.HelloReply)
        service_obj.add_stream_stream("SayHelloToMany", self.SayHelloToMany,
                                      greeter_pb2.HelloRequest, greeter_pb2.HelloReply)
        service_obj.add_stream_unary(
            "SayHelloToManyAtOnce", self.SayHelloToManyAtOnce, greeter_pb2.HelloRequest,
            greeter_pb2.HelloReply)
        return service_obj
