import purerpc
import generated.greeter_pb2


class GreeterServicer(purerpc.Servicer):
    async def SayHello(self, input_message):
        raise NotImplementedError()

    async def SayHelloGoodbye(self, input_message):
        raise NotImplementedError()

    async def SayHelloToMany(self, input_messages):
        raise NotImplementedError()

    async def SayHelloToManyAtOnce(self, input_messages):
        raise NotImplementedError()

    @property
    def service(self) -> purerpc.Service:
        service_obj = purerpc.Service(
            "Greeter"
        )
        service_obj.add_method(
            "SayHello",
            self.SayHello,
            purerpc.RPCSignature(
                purerpc.Cardinality.UNARY_UNARY,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )
        service_obj.add_method(
            "SayHelloGoodbye",
            self.SayHelloGoodbye,
            purerpc.RPCSignature(
                purerpc.Cardinality.UNARY_STREAM,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )
        service_obj.add_method(
            "SayHelloToMany",
            self.SayHelloToMany,
            purerpc.RPCSignature(
                purerpc.Cardinality.STREAM_STREAM,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )
        service_obj.add_method(
            "SayHelloToManyAtOnce",
            self.SayHelloToManyAtOnce,
            purerpc.RPCSignature(
                purerpc.Cardinality.STREAM_UNARY,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )
        return service_obj


class GreeterStub:
    def __init__(self, channel):
        self._client = purerpc.Client(
            "Greeter",
            channel
        )
        self.SayHello = self._client.get_method_stub(
            "SayHello",
            purerpc.RPCSignature(
                purerpc.Cardinality.UNARY_UNARY,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )
        self.SayHelloGoodbye = self._client.get_method_stub(
            "SayHelloGoodbye",
            purerpc.RPCSignature(
                purerpc.Cardinality.UNARY_STREAM,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )
        self.SayHelloToMany = self._client.get_method_stub(
            "SayHelloToMany",
            purerpc.RPCSignature(
                purerpc.Cardinality.STREAM_STREAM,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )
        self.SayHelloToManyAtOnce = self._client.get_method_stub(
            "SayHelloToManyAtOnce",
            purerpc.RPCSignature(
                purerpc.Cardinality.STREAM_UNARY,
                generated.greeter_pb2.HelloRequest,
                generated.greeter_pb2.HelloReply,
            )
        )