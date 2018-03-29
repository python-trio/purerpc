import logging
import datetime

import h2.errors
import h2.events
import h2.connection
import h2.exceptions

from .config import GRPCConfiguration
from .events import MessageReceived, RequestReceived, RequestEnded, ResponseReceived, ResponseEnded
from .exceptions import ProtocolError
from .message_buffer import MessageBuffer

logger = logging.getLogger(__name__)


class GRPCConnection:
    def __init__(self, config: GRPCConfiguration):
        self.config = config
        self.h2_connection = h2.connection.H2Connection(config.h2_config)
        self.input_message_buffers = {}
        self.output_message_buffers = {}

    def _request_received(self, event: h2.events.RequestReceived):
        if event.stream_ended:
            raise ProtocolError("Stream ended before data was sent")
        request = RequestReceived.parse_from_stream_id_and_headers_destructive(
            event.stream_id, dict(event.headers))
        self.input_message_buffers[event.stream_id] = MessageBuffer(request.message_encoding)
        return [request]

    def _response_received(self, event: h2.events.ResponseReceived):
        headers = dict(event.headers)
        response_received = ResponseReceived.parse_from_stream_id_and_headers_destructive(
            event.stream_id, headers)
        if event.stream_ended:
            response_ended = ResponseEnded.parse_from_stream_id_and_headers_destructive(
                event.stream_id, headers)
            return [response_received, response_ended]
        else:
            if len(headers) > 0:
                raise ProtocolError("Unparsed headers: {}".format(headers))
            self.input_message_buffers[event.stream_id] = MessageBuffer(
                response_received.message_encoding)
            return [response_received]

    def _trailers_received(self, event: h2.events.TrailersReceived):
        response_ended = ResponseEnded.parse_from_stream_id_and_headers_destructive(
            event.stream_id, dict(event.headers))
        return [response_ended]

    def _informational_response_received(self, event: h2.events.InformationalResponseReceived):
        raise NotImplementedError()

    def _data_received(self, event: h2.events.DataReceived):
        try:
            self.input_message_buffers[event.stream_id].write(event.data)
        except KeyError:
            self.h2_connection.reset_stream(event.stream_id, h2.errors.ErrorCodes.PROTOCOL_ERROR)
        else:
            self.h2_connection.acknowledge_received_data(event.flow_controlled_length,
                                                         event.stream_id)
        events = []
        for message in self.input_message_buffers[event.stream_id].read_all_complete_messages():
            events.append(MessageReceived(event.stream_id, message))
        return events

    def _window_updated(self, event: h2.events.WindowUpdated):
        # TODO: implement this
        return []

    def _remote_settings_changed(self, event: h2.events.RemoteSettingsChanged):
        # TODO: implement this
        return []

    def _ping_acknowledged(self, event: h2.events.PingAcknowledged):
        raise NotImplementedError()

    def _stream_ended(self, event: h2.events.StreamEnded):
        if event.stream_id in self.input_message_buffers:
            del self.input_message_buffers[event.stream_id]
            return [RequestEnded(event.stream_id)]
        return []

    def _stream_reset(self, event: h2.events.StreamReset):
        raise NotImplementedError()

    def _push_stream_received(self, event: h2.events.PushedStreamReceived):
        raise NotImplementedError()

    def _settings_acknowledged(self, event: h2.events.SettingsAcknowledged):
        # TODO: implement this
        return []

    def _priority_updated(self, event: h2.events.PriorityUpdated):
        raise NotImplementedError()

    def _connection_terminated(self, event: h2.events.ConnectionTerminated):
        raise NotImplementedError()

    def _alternative_service_available(self, event: h2.events.AlternativeServiceAvailable):
        raise NotImplementedError()

    def _unknown_frame_received(self, event: h2.events.UnknownFrameReceived):
        raise NotImplementedError()

    HANDLER_MAP = {
        h2.events.RequestReceived: _request_received,
        h2.events.ResponseReceived: _response_received,
        h2.events.TrailersReceived: _trailers_received,
        h2.events.InformationalResponseReceived: _informational_response_received,
        h2.events.DataReceived: _data_received,
        h2.events.WindowUpdated: _window_updated,
        h2.events.RemoteSettingsChanged: _remote_settings_changed,
        h2.events.PingAcknowledged: _ping_acknowledged,
        h2.events.StreamEnded: _stream_ended,
        h2.events.StreamReset: _stream_reset,
        h2.events.PushedStreamReceived: _push_stream_received,
        h2.events.SettingsAcknowledged: _settings_acknowledged,
        h2.events.PriorityUpdated: _priority_updated,
        h2.events.ConnectionTerminated: _connection_terminated,
        h2.events.AlternativeServiceAvailable: _alternative_service_available,
        h2.events.UnknownFrameReceived: _unknown_frame_received,
    }

    def initiate_connection(self):
        self.h2_connection.initiate_connection()

    def data_to_send(self, amount: int = None):
        return self.h2_connection.data_to_send(amount)

    def receive_data(self, data: bytes):
        events = self.h2_connection.receive_data(data)
        grpc_events = []
        for event in events:
            logger.info("Get event: {}".format(event))
            grpc_events.extend(self.HANDLER_MAP[type(event)](self, event))
        return grpc_events

    def send_message(self, stream_id: int, message: bytes, compress=False):
        message_buffer = self.output_message_buffers[stream_id]
        message_buffer.write_complete_message(message, compress)
        self.h2_connection.send_data(stream_id, message_buffer.read())

    def start_request(self, stream_id: int, scheme: str, service_name: str, method_name: str,
                      message_type=None, authority=None, timeout: datetime.timedelta=None,
                      content_type_suffix="", custom_metadata=()):
        self.output_message_buffers[stream_id] = MessageBuffer(self.config.message_encoding)
        headers = [
            (":method", "POST"),
            (":scheme", scheme),
            (":path", "/{}/{}".format(service_name, method_name)),
            ("te", "trailers"),
            ("content-type", "application/grpc" + content_type_suffix),
            *custom_metadata
        ]
        if authority is not None:
            headers.insert(3, (":authority", authority))
        if timeout is not None:
            number_of_whole_seconds = timeout.days * 86400 + timeout.seconds
            if timeout.microseconds == 0:
                timeout_unit = "S"
                timeout_value = number_of_whole_seconds
            else:
                timeout_unit = "u"
                timeout_value = number_of_whole_seconds * 1000000 + timeout.microseconds
            timeout_str = "{}{}".format(timeout_value, timeout_unit)
            headers.insert(4, ("grpc-timeout", timeout_str))
        if message_type is not None:
            headers.append(("grpc-message-type", message_type))
        if self.config.message_encoding is not None:
            headers.append(("grpc-encoding", self.config.message_encoding))
        if self.config.message_accept_encoding is not None:
            headers.append(("grpc-accept-encoding", self.config.message_accept_encoding))
        if self.config.user_agent is not None:
            headers.append(("user-agent", self.config.user_agent))
        self.h2_connection.send_headers(stream_id, headers, end_stream=False)

    def end_request(self, stream_id: int):
        del self.output_message_buffers[stream_id]
        self.h2_connection.send_data(stream_id, b"", end_stream=True)

    def start_response(self, stream_id: int, content_type_suffix="", custom_metadata=()):
        self.output_message_buffers[stream_id] = MessageBuffer(self.config.message_encoding)
        headers = [
            (":status", "200"),
            ("content-type", "application/grpc" + content_type_suffix),
            *custom_metadata,
        ]
        if self.config.message_encoding is not None:
            headers.append(("grpc-encoding", self.config.message_encoding))
        if self.config.message_accept_encoding is not None:
            headers.append(("grpc-accept-encoding", self.config.message_accept_encoding))
        self.h2_connection.send_headers(stream_id, headers, end_stream=False)

    def end_response(self, stream_id: int, status: int, status_message=None, custom_metadata=()):
        del self.output_message_buffers[stream_id]
        headers = [
            ("grpc-status", str(status)),
            *custom_metadata,
        ]
        if status_message is not None:
            # TODO: should be percent encoded
            headers.append(("grpc-message", status_message))
        self.h2_connection.send_headers(stream_id, headers, end_stream=True)
