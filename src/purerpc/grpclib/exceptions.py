class GRPCError(Exception):
    pass


class ProtocolError(GRPCError):
    pass


class UnsupportedMessageEncodingError(ProtocolError):
    pass


# TODO: add tests for status codes in client
# TODO: add tests that check correct package name
# TODO: add tests for correct status codes in server
# TODO: organize data folder by test names
class RemoteCallFailedError(GRPCError):
    def __init__(self, status):
        super().__init__(f"Remote call failed with status {status}")
