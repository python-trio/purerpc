import curio
from purerpc.grpc_proto import GRPCProtoSocket
import functools
from purerpc.grpclib.config import GRPCConfiguration
from purerpc.rpc import RPCSignature, Cardinality
from purerpc.wrappers import ClientStubUnaryUnary, ClientStubStreamStream, ClientStubUnaryStream, \
    ClientStubStreamUnary


class Channel:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.grpc_socket = None

    async def connect(self):
        socket = await curio.open_connection(self.host, self.port)
        config = GRPCConfiguration(client_side=True)
        self.grpc_socket = GRPCProtoSocket(config, socket)
        await self.grpc_socket.initiate_connection()


class Client:
    def __init__(self, service_name: str, channel: Channel):
        self.service_name = service_name
        self.channel = channel

    async def rpc(self, method_name: str, request_type, response_type, metadata=None):
        if self.channel.grpc_socket is None:
            await self.channel.connect()
        message_type = request_type.DESCRIPTOR.full_name
        if metadata is None:
            metadata = ()
        stream = await self.channel.grpc_socket.start_request("http", self.service_name,
                                                              method_name, message_type,
                                                              "{}:{}".format(self.channel.host,
                                                                             self.channel.port),
                                                              custom_metadata=metadata)
        stream.expect_message_type(response_type)
        return stream

    def get_method_stub(self, method_name: str, signature: RPCSignature):
        stream_fn = functools.partial(self.rpc, method_name, signature.request_type,
                                      signature.response_type)
        if signature.cardinality == Cardinality.STREAM_STREAM:
            return ClientStubStreamStream(stream_fn)
        elif signature.cardinality == Cardinality.UNARY_STREAM:
            return ClientStubUnaryStream(stream_fn)
        elif signature.cardinality == Cardinality.STREAM_UNARY:
            return ClientStubStreamUnary(stream_fn)
        else:
            return ClientStubUnaryUnary(stream_fn)
