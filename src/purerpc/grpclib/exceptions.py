from .status import Status, StatusCode


class GRPCError(Exception):
    pass


class StreamClosedError(GRPCError):
    def __init__(self, stream_id, error_code):
        self.stream_id = stream_id
        self.error_code = error_code


class ProtocolError(GRPCError):
    pass


class MessageTooLargeError(ProtocolError):
    pass


class UnsupportedMessageEncodingError(ProtocolError):
    pass


class RpcFailedError(GRPCError):
    def __init__(self, status):
        super().__init__("RPC failed with status {status}".format(status=status))
        self._status = status

    @property
    def status(self):
        return self._status


class CancelledError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.CANCELLED, message))


class UnknownError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.UNKNOWN, message))


class InvalidArgumentError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.INVALID_ARGUMENT, message))


class DeadlineExceededError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.DEADLINE_EXCEEDED, message))


class NotFoundError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.NOT_FOUND, message))


class AlreadyExistsError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.ALREADY_EXISTS, message))


class PermissionDeniedError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.PERMISSION_DENIED, message))


class ResourceExhaustedError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.RESOURCE_EXHAUSTED, message))


class FailedPreconditionError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.FAILED_PRECONDITION, message))


class AbortedError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.ABORTED, message))


class OutOfRangeError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.OUT_OF_RANGE, message))


class UnimplementedError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.UNIMPLEMENTED, message))


class InternalError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.INTERNAL, message))


class UnavailableError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.UNAVAILABLE, message))


class DataLossError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.DATA_LOSS, message))


class UnauthenticatedError(RpcFailedError):
    def __init__(self, message=""):
        super().__init__(Status(StatusCode.UNAUTHENTICATED, message))


def raise_status(status: Status):
    if status.status_code == StatusCode.CANCELLED:
        raise CancelledError(status.status_message)
    elif status.status_code == StatusCode.UNKNOWN:
        raise UnknownError(status.status_message)
    elif status.status_code == StatusCode.INVALID_ARGUMENT:
        raise InvalidArgumentError(status.status_message)
    elif status.status_code == StatusCode.DEADLINE_EXCEEDED:
        raise DeadlineExceededError(status.status_message)
    elif status.status_code == StatusCode.NOT_FOUND:
        raise NotFoundError(status.status_message)
    elif status.status_code == StatusCode.ALREADY_EXISTS:
        raise AlreadyExistsError(status.status_message)
    elif status.status_code == StatusCode.PERMISSION_DENIED:
        raise PermissionDeniedError(status.status_message)
    elif status.status_code == StatusCode.RESOURCE_EXHAUSTED:
        raise ResourceExhaustedError(status.status_message)
    elif status.status_code == StatusCode.FAILED_PRECONDITION:
        raise FailedPreconditionError(status.status_message)
    elif status.status_code == StatusCode.ABORTED:
        raise AbortedError(status.status_message)
    elif status.status_code == StatusCode.OUT_OF_RANGE:
        raise OutOfRangeError(status.status_message)
    elif status.status_code == StatusCode.UNIMPLEMENTED:
        raise UnimplementedError(status.status_message)
    elif status.status_code == StatusCode.INTERNAL:
        raise InternalError(status.status_message)
    elif status.status_code == StatusCode.UNAVAILABLE:
        raise UnavailableError(status.status_message)
    elif status.status_code == StatusCode.DATA_LOSS:
        raise DataLossError(status.status_message)
    elif status.status_code == StatusCode.UNAUTHENTICATED:
        raise UnauthenticatedError(status.status_message)
