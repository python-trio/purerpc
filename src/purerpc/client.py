import functools

import anyio
import async_exit_stack

from purerpc.grpc_proto import GRPCProtoSocket
from purerpc.grpclib.config import GRPCConfiguration
from purerpc.rpc import RPCSignature, Cardinality
from purerpc.wrappers import ClientStubUnaryUnary, ClientStubStreamStream, ClientStubUnaryStream, \
    ClientStubStreamUnary


class _Channel(async_exit_stack.AsyncExitStack):
    def __init__(self, host, port):
        super().__init__()
        self._host = host
        self._port = port
        self._grpc_socket = None

    async def __aenter__(self):
        await super().__aenter__()  # Does nothing

        background_task_group = await self.enter_async_context(anyio.create_task_group())
        self.push_async_callback(background_task_group.cancel_scope.cancel)

        socket = await anyio.connect_tcp(self._host, self._port, autostart_tls=False, tls_standard_compatible=False)
        config = GRPCConfiguration(client_side=True)
        self._grpc_socket = GRPCProtoSocket(config, socket)
        await self._grpc_socket.initiate_connection(background_task_group)
        return self


def insecure_channel(host, port):
    return _Channel(host, port)


class Client:
    def __init__(self, service_name: str, channel: _Channel):
        self.service_name = service_name
        self.channel = channel

    async def rpc(self, method_name: str, request_type, response_type, metadata=None):
        message_type = request_type.DESCRIPTOR.full_name
        if metadata is None:
            metadata = ()
        stream = await self.channel._grpc_socket.start_request("http", self.service_name,
                                                               method_name, message_type,
                                                              "{}:{}".format(self.channel._host,
                                                                             self.channel._port),
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
