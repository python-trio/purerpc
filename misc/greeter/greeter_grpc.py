import purerpc.server
import purerpc.client
from purerpc.rpc import Cardinality, RPCSignature
import greeter_pb2


class GreeterServicer(purerpc.server.Servicer):
    async def SayHello(self, input_message):
        raise NotImplementedError()

    async def SayHelloGoodbye(self, input_message):
        raise NotImplementedError()

    async def SayHelloToMany(self, input_messages):
        raise NotImplementedError()

    async def SayHelloToManyAtOnce(self, input_messages):
        raise NotImplementedError()

    @property
    def service(self) -> purerpc.server.Service:
        service_obj = purerpc.server.Service("Greeter")
        service_obj.add_method("SayHello", self.SayHello, RPCSignature(
            Cardinality.UNARY_UNARY, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
        service_obj.add_method("SayHelloGoodbye", self.SayHelloGoodbye, RPCSignature(
            Cardinality.UNARY_STREAM, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
        service_obj.add_method("SayHelloToMany", self.SayHelloToMany, RPCSignature(
            Cardinality.STREAM_STREAM, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
        service_obj.add_method("SayHelloToManyAtOnce", self.SayHelloToManyAtOnce, RPCSignature(
            Cardinality.STREAM_UNARY, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
        return service_obj


class GreeterStub:
    def __init__(self, channel):
        self._stub = purerpc.client.Stub("Greeter", channel)
        self.SayHello = self._stub.get_method_stub("SayHello", RPCSignature(
            Cardinality.UNARY_UNARY, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
        self.SayHelloGoodbye = self._stub.get_method_stub("SayHelloGoodbye", RPCSignature(
            Cardinality.UNARY_STREAM, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
        self.SayHelloToMany = self._stub.get_method_stub("SayHelloToMany", RPCSignature(
            Cardinality.STREAM_STREAM, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
        self.SayHelloToManyAtOnce = self._stub.get_method_stub("SayHelloToManyAtOnce", RPCSignature(
            Cardinality.STREAM_UNARY, greeter_pb2.HelloRequest, greeter_pb2.HelloReply))
