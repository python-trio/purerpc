import enum
import typing
import collections
import collections.abc


Stream = typing.AsyncIterator


class Cardinality(enum.Enum):
    UNARY_UNARY = 0
    UNARY_STREAM = 1
    STREAM_UNARY = 2
    STREAM_STREAM = 3

    @staticmethod
    def get_cardinality_for(*, request_stream, response_stream):
        if request_stream and response_stream:
            return Cardinality.STREAM_STREAM
        elif request_stream and not response_stream:
            return Cardinality.STREAM_UNARY
        elif not request_stream and response_stream:
            return Cardinality.UNARY_STREAM
        else:
            return Cardinality.UNARY_UNARY


class RPCSignature:
    def __init__(self, cardinality: Cardinality, request_type, response_type):
        self._cardinality = cardinality
        self._request_type = request_type
        self._response_type = response_type

    @property
    def cardinality(self):
        return self._cardinality

    @property
    def request_type(self):
        return self._request_type

    @property
    def response_type(self):
        return self._response_type

    @staticmethod
    def from_annotations(request_annotation, response_annotation):
        if (hasattr(request_annotation, "__origin__") and
                issubclass(request_annotation.__origin__, collections.abc.AsyncIterator)):
            request_type = request_annotation.__args__[0]
            request_stream = True
        else:
            request_type = request_annotation
            request_stream = False

        if (hasattr(response_annotation, "__origin__") and
                issubclass(response_annotation.__origin__, collections.abc.AsyncIterator)):
            response_type = response_annotation.__args__[0]
            response_stream = True
        else:
            response_type = response_annotation
            response_stream = False
        cardinality = Cardinality.get_cardinality_for(request_stream=request_stream,
                                                      response_stream=response_stream)
        return RPCSignature(cardinality, request_type, response_type)
