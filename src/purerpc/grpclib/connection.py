import logging
import datetime

import h2.errors
import h2.events
import h2.connection
import h2.exceptions
from h2.settings import SettingCodes

from .config import GRPCConfiguration
from .events import MessageReceived, RequestReceived, RequestEnded, ResponseReceived, ResponseEnded
from .exceptions import ProtocolError
from .buffers import MessageReadBuffer, MessageWriteBuffer

logger = logging.getLogger(__name__)


class GRPCConnection:
    def __init__(self, config: GRPCConfiguration):
        self.config = config
        self.h2_connection = h2.connection.H2Connection(config._h2_config)
        self.message_read_buffers = {}

        # if stream_id in this dict, that means that write stream end was requested and the
        # corresponding value are the trailers that should be sent by data_to_send() or None if
        # we should just end the stream
        # data_to_send method is responsible for clearing all of the data structures below when
        # the corresponding stream has ended
        self.stream_write_trailers = {}
        self.message_write_buffers = {}
        self.stream_write_pending = set()

    def _request_received(self, event: h2.events.RequestReceived):
        if event.stream_ended:
            raise ProtocolError("Stream ended before data was sent")
        request = RequestReceived.parse_from_stream_id_and_headers_destructive(
            event.stream_id, dict(event.headers))
        self.message_read_buffers[event.stream_id] = MessageReadBuffer(request.message_encoding)
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
            self.message_read_buffers[event.stream_id] = MessageReadBuffer(
                response_received.message_encoding)
            return [response_received]

    def _trailers_received(self, event: h2.events.TrailersReceived):
        response_ended = ResponseEnded.parse_from_stream_id_and_headers_destructive(
            event.stream_id, dict(event.headers))
        return [response_ended]

    def _informational_response_received(self, event: h2.events.InformationalResponseReceived):
        return []

    def _data_received(self, event: h2.events.DataReceived):
        try:
            self.message_read_buffers[event.stream_id].data_received(event.data)
        except KeyError:
            self.h2_connection.reset_stream(event.stream_id, h2.errors.ErrorCodes.PROTOCOL_ERROR)
        else:
            self.h2_connection.acknowledge_received_data(event.flow_controlled_length,
                                                         event.stream_id)
        events = []
        for message in self.message_read_buffers[event.stream_id].read_all_complete_messages():
            events.append(MessageReceived(event.stream_id, message))
        return events

    def _window_updated(self, event: h2.events.WindowUpdated):
        # TODO: implement this
        return []

    def _remote_settings_changed(self, event: h2.events.RemoteSettingsChanged):
        # TODO: implement this
        return []

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
        # TODO: implement this
        return []

    def _priority_updated(self, event: h2.events.PriorityUpdated):
        return []

    def _connection_terminated(self, event: h2.events.ConnectionTerminated):
        return []

    def _alternative_service_available(self, event: h2.events.AlternativeServiceAvailable):
        return []

    def _unknown_frame_received(self, event: h2.events.UnknownFrameReceived):
        return []

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
        self.h2_connection.update_settings({
            SettingCodes.MAX_CONCURRENT_STREAMS: 1000,
            SettingCodes.INITIAL_WINDOW_SIZE: 128 * 1024,
            SettingCodes.MAX_FRAME_SIZE: 128 * 1024,
        })

    def data_to_send(self, amount: int = None):
        stream_write_pending_remove_flag = []
        # TODO: computations may be too heavy when repeatedly calling data_to_send with small amount
        for stream_id in self.stream_write_pending:
            num_bytes_to_send = min(self.h2_connection.max_outbound_frame_size,
                                    self.h2_connection.local_flow_control_window(stream_id),
                                    len(self.message_write_buffers[stream_id]))
            data_to_send = self.message_write_buffers[stream_id].data_to_send(num_bytes_to_send)
            self.h2_connection.send_data(stream_id, data_to_send)
            if len(self.message_write_buffers[stream_id]) == 0:
                stream_write_pending_remove_flag.append(stream_id)
        for stream_id in stream_write_pending_remove_flag:
            self.stream_write_pending.remove(stream_id)

        stream_ended = []
        for stream_id, trailers in self.stream_write_trailers.items():
            if stream_id not in self.stream_write_pending:
                if trailers is None:
                    self.h2_connection.send_data(stream_id, b"", end_stream=True)
                else:
                    self.h2_connection.send_headers(stream_id, trailers, end_stream=True)
                stream_ended.append(stream_id)
        for stream_id in stream_ended:
            del self.stream_write_trailers[stream_id]
            del self.message_write_buffers[stream_id]

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

    # API to apply backpressure for send_message
    def write_buffer_size(self, stream_id: int):
        if stream_id in self.message_write_buffers:
            return len(self.message_write_buffers[stream_id])
        else:
            return 0

    def send_message(self, stream_id: int, message: bytes, compress=False):
        self.message_write_buffers[stream_id].write_message(message, compress)
        self.stream_write_pending.add(stream_id)

    def get_next_available_stream_id(self):
        return self.h2_connection.get_next_available_stream_id()

    def start_request(self, stream_id: int, scheme: str, service_name: str, method_name: str,
                      message_type=None, authority=None, timeout: datetime.timedelta=None,
                      content_type_suffix="", custom_metadata=()):
        self.message_write_buffers[stream_id] = MessageWriteBuffer(self.config._message_encoding)
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
        if self.config._message_encoding is not None:
            headers.append(("grpc-encoding", self.config._message_encoding))
        if self.config._message_accept_encoding is not None:
            headers.append(("grpc-accept-encoding", self.config._message_accept_encoding))
        if self.config._user_agent is not None:
            headers.append(("user-agent", self.config._user_agent))
        self.h2_connection.send_headers(stream_id, headers, end_stream=False)

    def end_request(self, stream_id: int):
        self.stream_write_trailers[stream_id] = None
        self.stream_write_pending.add(stream_id)

    def start_response(self, stream_id: int, content_type_suffix="", custom_metadata=()):
        self.message_write_buffers[stream_id] = MessageWriteBuffer(self.config._message_encoding)
        headers = [
            (":status", "200"),
            ("content-type", "application/grpc" + content_type_suffix),
            *custom_metadata,
        ]
        if self.config._message_encoding is not None:
            headers.append(("grpc-encoding", self.config._message_encoding))
        if self.config._message_accept_encoding is not None:
            headers.append(("grpc-accept-encoding", self.config._message_accept_encoding))
        self.h2_connection.send_headers(stream_id, headers, end_stream=False)

    def end_response(self, stream_id: int, status: int, status_message=None, custom_metadata=()):
        trailers = [
            ("grpc-status", str(status)),
            *custom_metadata,
        ]
        if status_message is not None:
            # TODO: should be percent encoded
            trailers.append(("grpc-message", status_message))
        self.stream_write_trailers[stream_id] = trailers
        self.stream_write_pending.add(stream_id)
