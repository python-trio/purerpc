import datetime

from purerpc.grpclib.events import MessageReceived, RequestEnded, ResponseEnded

from .grpc_socket import GRPCStream, GRPCSocket


class GRPCProtoStream(GRPCStream):
    def expect_message_type(self, message_type):
        self._incoming_message_type = message_type

    async def send_message(self, message):
        return await super()._send(message.SerializeToString())

    async def receive_event(self):
        event = await super()._receive()
        if isinstance(event, MessageReceived) and hasattr(self, "_incoming_message_type"):
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

    async def start_response(self, content_type_suffix="", custom_metadata=()):
        return await super().start_response(
            content_type_suffix if content_type_suffix else "+proto",
            custom_metadata)


class GRPCProtoSocket(GRPCSocket):
    StreamClass = GRPCProtoStream

    async def start_request(self, scheme: str, service_name: str, method_name: str,
                            message_type=None, authority=None, timeout: datetime.timedelta = None,
                            content_type_suffix="", custom_metadata=()):
        return await super().start_request(
            scheme, service_name, method_name, message_type, authority, timeout,
            content_type_suffix if content_type_suffix else "+proto", custom_metadata
        )
