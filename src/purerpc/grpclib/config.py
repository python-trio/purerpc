import h2.config


class GRPCConfiguration:
    def __init__(self, client_side: bool, server_string=None, user_agent=None,
                 message_encoding=None, message_accept_encoding=None):
        self.h2_config = h2.config.H2Configuration(client_side=client_side, header_encoding="utf-8")
        if client_side and server_string is not None:
            raise ValueError("Passed client_side=True and server_string at the same time")
        if not client_side and user_agent is not None:
            raise ValueError("Passed user_agent put didn't pass client_side=True")
        self.server_string = server_string
        self.user_agent = user_agent
        self.message_encoding = message_encoding
        if message_accept_encoding is not None:
            self.message_accept_encoding = ",".join(message_accept_encoding)
        else:
            self.message_accept_encoding = None

