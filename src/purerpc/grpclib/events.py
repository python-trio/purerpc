import urllib.parse
import datetime

from .headers import HeaderDict
from .exceptions import ProtocolError
from .status import Status


class Event:
    pass


class WindowUpdated(Event):
    def __init__(self, stream_id, delta):
        self.stream_id = stream_id
        self.delta = delta

    def __repr__(self):
        return "<WindowUpdated stream_id:%s, delta:%s>" % (
            self.stream_id, self.delta
        )



class RequestReceived(Event):
    def __init__(self, stream_id: int, scheme: str, service_name: str, method_name: str,
                 content_type: str):
        self.stream_id = stream_id
        self.scheme = scheme
        self.service_name = service_name
        self.method_name = method_name
        self.content_type = content_type
        self.authority = None
        self.timeout = None
        self.message_type = None
        self.message_encoding = None
        self.message_accept_encoding = None
        self.user_agent = None
        self.custom_metadata = ()

    @staticmethod
    def parse_from_stream_id_and_headers_destructive(stream_id: int, headers: HeaderDict):
        if headers.pop(":method") != "POST":
            raise ProtocolError("Unsupported method {}".format(headers[":method"]))

        scheme = headers.pop(":scheme")
        if scheme not in ["http", "https"]:
            raise ProtocolError("Scheme should be either http or https")

        if headers[":path"].startswith("/"):
            service_name, method_name = headers.pop(":path")[1:].split("/")
        else:
            raise ProtocolError("Path should be /<service_name>/<method_name>")

        if "te" not in headers or headers["te"] != "trailers":
            raise ProtocolError("te header not found or not equal to 'trailers', "
                                "using incompatible proxy?")
        else:
            headers.pop("te")

        content_type = headers.pop("content-type")
        if not content_type.startswith("application/grpc"):
            raise ProtocolError("Content type should start with application/grpc")

        event = RequestReceived(stream_id, scheme, service_name, method_name, content_type)

        if ":authority" in headers:
            event.authority = headers.pop(":authority")

        if "grpc-timeout" in headers:
            timeout_string = headers.pop("grpc-timeout")
            timeout_value, timeout_unit = int(timeout_string[:-1]), timeout_string[-1:]
            if timeout_unit == "H":
                event.timeout = datetime.timedelta(hours=timeout_value)
            elif timeout_unit == "M":
                event.timeout = datetime.timedelta(minutes=timeout_value)
            elif timeout_unit == "S":
                event.timeout = datetime.timedelta(seconds=timeout_value)
            elif timeout_unit == "m":
                event.timeout = datetime.timedelta(milliseconds=timeout_value)
            elif timeout_unit == "u":
                event.timeout = datetime.timedelta(microseconds=timeout_value)
            elif timeout_unit == "n":
                event.timeout = datetime.timedelta(microseconds=timeout_value / 1000)
            else:
                raise ProtocolError("Unknown timeout unit: {}".format(timeout_unit))

        if "grpc-encoding" in headers:
            event.message_encoding = headers.pop("grpc-encoding")

        if "grpc-accept-encoding" in headers:
            event.message_accept_encoding = headers.pop("grpc-accept-encoding").split(",")

        if "user-agent" in headers:
            event.user_agent = headers.pop("user-agent")

        if "grpc-message-type" in headers:
            event.message_type = headers.pop("grpc-message-type")

        event.custom_metadata = tuple(header for header_name in list(headers.keys())
                                      for header in headers.extract_headers(header_name))
        return event

    def __repr__(self):
        fmt_string = ("<purerpc.grpclib.events.RequestReceived stream_id: {stream_id}, "
                      "service_name: {service_name}, method_name: {method_name}>")
        return fmt_string.format(
            stream_id=self.stream_id,
            service_name=self.service_name,
            method_name=self.method_name,
        )


class MessageReceived(Event):
    def __init__(self, stream_id: int, data: bytes, flow_controlled_length: int):
        self.stream_id = stream_id
        self.data = data
        self.flow_controlled_length = flow_controlled_length

    def __repr__(self):
        fmt_string= ("<purerpc.grpclib.events.MessageReceived stream_id: {stream_id}, "
                     "flow_controlled_length: {flow_controlled_length}>")
        return fmt_string.format(
            stream_id=self.stream_id,
            flow_controlled_length=self.flow_controlled_length,
        )


class RequestEnded(Event):
    def __init__(self, stream_id: int):
        self.stream_id = stream_id

    def __repr__(self):
        fmt_string = "<purerpc.grpclib.events.RequestEnded stream_id: {stream_id}>"
        return fmt_string.format(
            stream_id=self.stream_id,
        )


class ResponseReceived(Event):
    def __init__(self, stream_id: int, content_type: str):
        self.stream_id = stream_id
        self.content_type = content_type
        self.message_encoding = None
        self.message_accept_encoding = None
        self.custom_metadata = ()

    @staticmethod
    def parse_from_stream_id_and_headers_destructive(stream_id: int, headers: HeaderDict):
        if int(headers.pop(":status")) != 200:
            raise ProtocolError("http status is not 200")

        content_type = headers.pop("content-type")
        if not content_type.startswith("application/grpc"):
            raise ProtocolError("Content type should start with application/grpc")

        event = ResponseReceived(stream_id, content_type)

        if "grpc-encoding" in headers:
            event.message_encoding = headers.pop("grpc-encoding")

        if "grpc-accept-encoding" in headers:
            event.message_accept_encoding = headers.pop("grpc-accept-encoding").split(",")

        event.custom_metadata = tuple(header for header_name in list(headers.keys())
                                      for header in headers.extract_headers(header_name))
        return event

    def __repr__(self):
        fmt_string = "<purerpc.grpclib.events.ResponseReceived stream_id: {stream_id} content_type: {content_type}>"
        return fmt_string.format(
            stream_id=self.stream_id,
            content_type=self.content_type,
        )


class ResponseEnded(Event):
    def __init__(self, stream_id: int, status: Status):
        self.stream_id = stream_id
        self.status = status
        self.custom_metadata = ()

    @staticmethod
    def parse_from_stream_id_and_headers_destructive(stream_id: int, headers: HeaderDict):
        if "grpc-status" not in headers:
            raise ProtocolError("Expected grpc-status in trailers")

        status_code = int(headers.pop("grpc-status"))
        if "grpc-message" in headers:
            status_message = urllib.parse.unquote(headers.pop("grpc-message"))
        else:
            status_message = ""

        event = ResponseEnded(stream_id, Status(status_code, status_message))

        event.custom_metadata = tuple(header for header_name in list(headers.keys())
                                      for header in headers.extract_headers(header_name))
        return event

    def __repr__(self):
        fmt_string = "<purerpc.grpclib.events.ResponseEnded stream_id: {stream_id}, status: {status}>"
        return fmt_string.format(
            stream_id=self.stream_id,
            status=self.status,
        )
