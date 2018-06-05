import datetime

import curio.io
from purerpc.grpclib.config import GRPCConfiguration
from purerpc.grpclib.events import MessageReceived, RequestEnded, ResponseEnded

from .grpc_socket import GRPCStream, GRPCSocket, StreamClose


class GRPCProtoStream(GRPCStream):
    def __init__(self, socket: "GRPCSocket", stream_id: int, client_side: bool,
                 incoming_buffer_size=10, outgoing_buffer_size=10):
        super().__init__(socket, stream_id, client_side, incoming_buffer_size, outgoing_buffer_size)
        self._incoming_message_type = None

    def expect_message_type(self, message_type):
        self._incoming_message_type = message_type

    async def send_message(self, message):
        return await super().send_message(message.SerializeToString())

    async def receive_event(self):
        event = await super().receive_event()
        if isinstance(event, MessageReceived) and self._incoming_message_type is not None:
            binary_data = event.data
            event.data = self._incoming_message_type()
            event.data.ParseFromString(binary_data)
        return event

    async def receive_message(self):
        event = await self.receive_event()
        if isinstance(event, RequestEnded) or isinstance(event, ResponseEnded):
            return None
        elif isinstance(event, MessageReceived):
            return event.data
        else:
            return await self.receive_message()

    async def close(self, status=None, status_message=None, custom_metadata=()):
        if self._client_side and (status or status_message or custom_metadata):
            raise ValueError("Client side streams cannot be closed with non-default arguments")
        await super().send_message(StreamClose(status, status_message, custom_metadata))

    async def start_response(self, stream_id: int, content_type_suffix="", custom_metadata=()):
        return await super().start_response(
            stream_id,
            content_type_suffix if content_type_suffix else "+proto",
            custom_metadata)


class GRPCProtoSocket(GRPCSocket):
    def _stream_ctor(self, stream_id):
        return GRPCProtoStream(self, stream_id, self.client_side)

    async def start_request(self, scheme: str, service_name: str, method_name: str,
                            message_type=None, authority=None, timeout: datetime.timedelta = None,
                            content_type_suffix="", custom_metadata=()):
        return await super().start_request(
            scheme, service_name, method_name, message_type, authority, timeout,
            content_type_suffix if content_type_suffix else "+proto", custom_metadata
        )
