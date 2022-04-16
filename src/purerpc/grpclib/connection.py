import urllib.parse
import logging
import datetime

import h2.config
import h2.events
import h2.connection
import h2.exceptions
from h2.settings import SettingCodes
from h2.errors import ErrorCodes

from .headers import HeaderDict, sanitize_headers
from .status import Status
from .config import GRPCConfiguration
from .events import MessageReceived, RequestReceived, RequestEnded, ResponseReceived, ResponseEnded, WindowUpdated
from .exceptions import ProtocolError, StreamClosedError
from .buffers import MessageReadBuffer
from ._h2_monkeypatch import apply_patch

# TODO: stop runtime patching of the h2 module
apply_patch()

logger = logging.getLogger(__name__)


class GRPCConnection:
    MAX_HEADER_LIST_SIZE = 8192
    MAX_CONCURRENT_STREAMS = 2 ** 16
    MAX_INBOUND_FRAME_SIZE = 2 ** 24 - 1

    def __init__(self, config: GRPCConfiguration):
        self.config = config
        self.h2_connection = h2.connection.H2Connection(h2.config.H2Configuration(client_side=config.client_side,
                                                                                  header_encoding="utf-8"))
        self.h2_connection.clear_outbound_data_buffer()
        self._set_h2_connection_local_settings()
        self.message_read_buffers = {}

    def _set_h2_connection_local_settings(self):
        self.h2_connection.local_settings = h2.settings.Settings(
            client=self.config.client_side,
            initial_values={
                SettingCodes.MAX_CONCURRENT_STREAMS: self.MAX_CONCURRENT_STREAMS,
                SettingCodes.INITIAL_WINDOW_SIZE: 2 * self.config.max_message_length,
                SettingCodes.MAX_FRAME_SIZE: self.MAX_INBOUND_FRAME_SIZE,
                SettingCodes.MAX_HEADER_LIST_SIZE: self.MAX_HEADER_LIST_SIZE,
            }
        )
        try:
            self.h2_connection.max_inbound_frame_size = self.MAX_INBOUND_FRAME_SIZE
        except AttributeError:
            pass

    def _request_received(self, event: h2.events.RequestReceived):
        if event.stream_ended:
            raise ProtocolError("Stream ended before data was sent")
        request = RequestReceived.parse_from_stream_id_and_headers_destructive(
            event.stream_id, HeaderDict(event.headers))
        self.message_read_buffers[event.stream_id] = MessageReadBuffer(request.message_encoding,
            self.config.max_message_length)
        return [request]

    def _response_received(self, event: h2.events.ResponseReceived):
        headers = HeaderDict(event.headers)
        response_received = ResponseReceived.parse_from_stream_id_and_headers_destructive(
            event.stream_id, headers)
        if event.stream_ended:
            response_ended = ResponseEnded.parse_from_stream_id_and_headers_destructive(
                event.stream_id, headers)
            return [response_received, response_ended]
        else:
            if len(headers) > 0:
                raise ProtocolError("Unparsed headers: {}".format(headers))
            self.message_read_buffers[event.stream_id] = MessageReadBuffer(
                response_received.message_encoding, self.config.max_message_length)
            return [response_received]

    def _trailers_received(self, event: h2.events.TrailersReceived):
        response_ended = ResponseEnded.parse_from_stream_id_and_headers_destructive(
            event.stream_id, HeaderDict(event.headers))
        return [response_ended]

    def _informational_response_received(self, event: h2.events.InformationalResponseReceived):
        return []

    def _data_received(self, event: h2.events.DataReceived):
        try:
            self.message_read_buffers[event.stream_id].data_received(event.data,
                                                                     event.flow_controlled_length)
        except KeyError:
            self.h2_connection.reset_stream(event.stream_id, ErrorCodes.PROTOCOL_ERROR)

        iterator = (self.message_read_buffers[event.stream_id]
                    .read_all_complete_messages_flowcontrol())
        events = []
        for message, flow_controlled_length in iterator:
            events.append(MessageReceived(event.stream_id, message, flow_controlled_length))
        return events

    def _window_updated(self, event: h2.events.WindowUpdated):
        return [WindowUpdated(stream_id=event.stream_id, delta=event.delta)]

    def _remote_settings_changed(self, event: h2.events.RemoteSettingsChanged):
        return [WindowUpdated(stream_id=0, delta=1)]

    def _ping_acknowledged(self, event: h2.events.PingAcknowledged):
        return []

    def _stream_ended(self, event: h2.events.StreamEnded):
        if event.stream_id in self.message_read_buffers:
            del self.message_read_buffers[event.stream_id]
            return [RequestEnded(event.stream_id)] if not self.config.client_side else []
        return []

    def _stream_reset(self, event: h2.events.StreamReset):
        return []

    def _push_stream_received(self, event: h2.events.PushedStreamReceived):
        return []

    def _settings_acknowledged(self, event: h2.events.SettingsAcknowledged):
        return []

    def _priority_updated(self, event: h2.events.PriorityUpdated):
        return []

    def _connection_terminated(self, event: h2.events.ConnectionTerminated):
        return []

    def _alternative_service_available(self, event: h2.events.AlternativeServiceAvailable):
        return []

    def _unknown_frame_received(self, event: h2.events.UnknownFrameReceived):
        return []

    def initiate_connection(self):
        self.h2_connection.initiate_connection()
        self.h2_connection.increment_flow_control_window(2 ** 30)

    def data_to_send(self, amount: int = None):
        return self.h2_connection.data_to_send(amount)

    def receive_data(self, data: bytes):
        events = self.h2_connection.receive_data(data)
        grpc_events = []
        for event in events:
            if isinstance(event, h2.events.RequestReceived):
                grpc_events.extend(self._request_received(event))
            elif isinstance(event, h2.events.ResponseReceived):
                grpc_events.extend(self._response_received(event))
            elif isinstance(event, h2.events.TrailersReceived):
                grpc_events.extend(self._trailers_received(event))
            elif isinstance(event, h2.events.InformationalResponseReceived):
                grpc_events.extend(self._informational_response_received(event))
            elif isinstance(event, h2.events.DataReceived):
                grpc_events.extend(self._data_received(event))
            elif isinstance(event, h2.events.WindowUpdated):
                grpc_events.extend(self._window_updated(event))
            elif isinstance(event, h2.events.RemoteSettingsChanged):
                grpc_events.extend(self._remote_settings_changed(event))
            elif isinstance(event, h2.events.PingAcknowledged):
                grpc_events.extend(self._ping_acknowledged(event))
            elif isinstance(event, h2.events.StreamEnded):
                grpc_events.extend(self._stream_ended(event))
            elif isinstance(event, h2.events.StreamReset):
                grpc_events.extend(self._stream_reset(event))
            elif isinstance(event, h2.events.PushedStreamReceived):
                grpc_events.extend(self._push_stream_received(event))
            elif isinstance(event, h2.events.SettingsAcknowledged):
                grpc_events.extend(self._settings_acknowledged(event))
            elif isinstance(event, h2.events.PriorityUpdated):
                grpc_events.extend(self._priority_updated(event))
            elif isinstance(event, h2.events.ConnectionTerminated):
                grpc_events.extend(self._connection_terminated(event))
            elif isinstance(event, h2.events.AlternativeServiceAvailable):
                grpc_events.extend(self._alternative_service_available(event))
            elif isinstance(event, h2.events.UnknownFrameReceived):
                grpc_events.extend(self._unknown_frame_received(event))

        return grpc_events

    def flow_control_window(self, stream_id: int):
        return min(self.h2_connection.max_outbound_frame_size,
                   self.h2_connection.local_flow_control_window(stream_id))

    def reset_stream(self, stream_id: int, error_code: h2.errors.ErrorCodes):
        self.h2_connection.reset_stream(stream_id, error_code)

    def acknowledge_received_data(self, stream_id: int, flow_controlled_length: int):
        self.h2_connection.acknowledge_received_data(flow_controlled_length, stream_id)

    def send_data(self, stream_id: int, data: bytes, end_stream: bool = False):
        self.h2_connection.send_data(stream_id, data, end_stream=end_stream)

    def get_next_available_stream_id(self):
        return self.h2_connection.get_next_available_stream_id()

    def start_request(self, stream_id: int, scheme: str, service_name: str, method_name: str,
                      message_type=None, authority=None, timeout: datetime.timedelta=None,
                      content_type_suffix="", custom_metadata=()):
        headers = [
            (":method", "POST"),
            (":scheme", scheme),
            (":path", "/{}/{}".format(service_name, method_name)),
            ("te", "trailers"),
            ("content-type", "application/grpc" + content_type_suffix),
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
        if self.config._message_encoding is not None:
            headers.append(("grpc-encoding", self.config._message_encoding))
        if self.config._message_accept_encoding is not None:
            headers.append(("grpc-accept-encoding", self.config._message_accept_encoding))
        if self.config._user_agent is not None:
            headers.append(("user-agent", self.config._user_agent))
        headers.extend(sanitize_headers(custom_metadata))
        self.h2_connection.send_headers(stream_id, headers, end_stream=False)

    def end_request(self, stream_id: int):
        try:
            self.h2_connection.send_data(stream_id, b"", end_stream=True)
        except h2.exceptions.StreamClosedError as e:
            raise StreamClosedError(stream_id=e.stream_id, error_code=e.error_code)

    def start_response(self, stream_id: int, content_type_suffix="", custom_metadata=()):
        headers = [
            (":status", "200"),
            ("content-type", "application/grpc" + content_type_suffix),
        ]
        if self.config._message_encoding is not None:
            headers.append(("grpc-encoding", self.config._message_encoding))
        if self.config._message_accept_encoding is not None:
            headers.append(("grpc-accept-encoding", self.config._message_accept_encoding))
        headers.extend(sanitize_headers(custom_metadata))
        self.h2_connection.send_headers(stream_id, headers, end_stream=False)

    def respond_status(self, stream_id: int, status: Status, content_type_suffix="",
                       custom_metadata=()):
        trailers = [
            (":status", "200"),
            ("content-type", "application/grpc" + content_type_suffix),
            ("grpc-status", str(status.int_value)),
        ]
        if status.status_message:
            trailers.append(("grpc-message", urllib.parse.quote(status.status_message, safe='')))
        trailers.extend(sanitize_headers(custom_metadata))
        self.h2_connection.send_headers(stream_id, trailers, end_stream=True)

    def end_response(self, stream_id: int, status: Status, custom_metadata=()):
        trailers = [
            ("grpc-status", str(status.int_value)),
        ]
        if status.status_message:
            trailers.append(("grpc-message", urllib.parse.quote(status.status_message, safe='')))
        trailers.extend(sanitize_headers(custom_metadata))
        self.h2_connection.send_headers(stream_id, trailers, end_stream=True)
