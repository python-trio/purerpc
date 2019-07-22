class GRPCConfiguration:
    def __init__(self, client_side: bool, server_string=None, user_agent=None,
                 message_encoding=None, message_accept_encoding=None,
                 max_message_length=33554432):
        self._client_side = client_side
        if client_side and server_string is not None:
            raise ValueError("Passed client_side=True and server_string at the same time")
        if not client_side and user_agent is not None:
            raise ValueError("Passed user_agent put didn't pass client_side=True")
        self._server_string = server_string
        self._user_agent = user_agent
        self._max_message_length = max_message_length
        self._message_encoding = message_encoding

        # TODO: this does not need to be passed in config, may be just a single global string
        # with all encodings supported by grpclib
        if message_accept_encoding is not None:
            self._message_accept_encoding = ",".join(message_accept_encoding)
        else:
            self._message_accept_encoding = None

    @property
    def client_side(self):
        return self._client_side

    @property
    def server_string(self):
        return self._server_string

    @property
    def user_agent(self):
        return self._user_agent

    @property
    def message_encoding(self):
        return self._message_encoding

    @property
    def message_accept_encoding(self):
        return self._message_accept_encoding

    @property
    def max_message_length(self):
        return self._max_message_length
