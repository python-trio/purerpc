import curio
from purerpc.grpc_socket import GRPCSocket
from purerpc.grpclib.connection import GRPCConnection
from purerpc.grpclib.config import GRPCConfiguration
from .grpclib.events import MessageReceived, ResponseReceived, ResponseEnded


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.grpc_socket = None

    async def connect(self):
        socket = await curio.open_connection(self.host, self.port)
        config = GRPCConfiguration(client_side=True)
        self.grpc_socket = GRPCSocket(config, socket)
        await self.grpc_socket.initiate_connection()
        await curio.spawn(self._read_thread(), daemon=True)

    async def _read_thread(self):
        async for event in self.grpc_socket.listen():
            if isinstance(event, ResponseReceived):
                pass
            elif isinstance(event, ResponseEnded):
                # TODO: put None to queue
                pass
            elif isinstance(event, MessageReceived):
                # TODO: put message in queue
                pass

    async def send(self, msg):
        # TODO: create new queue, start sending messages
        # TODO: wait on queue to recv data
        pass
