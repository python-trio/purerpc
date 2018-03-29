
class GRPCError(RuntimeError):
    pass


class UnsupportedMessageEncodingError(RuntimeError):
    pass


class ProtocolError(GRPCError):
    pass