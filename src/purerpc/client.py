import curio
from purerpc.grpc_socket import GRPCSocket
from purerpc.grpclib.connection import GRPCConnection
from purerpc.grpclib.config import GRPCConfiguration
from .grpclib.events import MessageReceived, ResponseReceived, ResponseEnded


class StreamWrapper:
    def __init__(self, stream, in_message_type, out_message_type):
        self.stream = stream
        self.in_message_type = in_message_type
        self.out_message_type = out_message_type

    async def send(self, message):
        await self.stream.send(message.SerializeToString())

    async def recv(self) -> "Event":
        event = await self.stream.recv()
        if isinstance(event, ResponseReceived):
            return await self.recv()
        elif isinstance(event, MessageReceived):
            message = self.out_message_type()
            message.ParseFromString(event.data)
            return message
        elif isinstance(event, ResponseEnded):
            return None
        else:
            raise ValueError("")

    async def close(self):
        await self.stream.close()


class Channel:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.grpc_socket = None

    async def connect(self):
        socket = await curio.open_connection(self.host, self.port)
        config = GRPCConfiguration(client_side=True)
        self.grpc_socket = GRPCSocket(config, socket)
        await self.grpc_socket.initiate_connection()


class Stub:
    def __init__(self, service_name: str, channel: Channel):
        self.service_name = service_name
        self.channel = channel

    async def rpc(self, method_name: str, in_message_type, out_message_type):
        if self.channel.grpc_socket is None:
            await self.channel.connect()
        message_type = in_message_type.DESCRIPTOR.full_name
        stream = await self.channel.grpc_socket.start_request("http", self.service_name,
                                                              method_name, message_type,
                                                              "{}:{}".format(self.channel.host,
                                                                             self.channel.port))
        return StreamWrapper(stream, in_message_type, out_message_type)

