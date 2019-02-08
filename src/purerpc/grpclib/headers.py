import base64
import collections


class HeaderDict(collections.OrderedDict):
    def __init__(self, values):
        super().__init__()
        for key, value in values:
            if key not in self:
                self[key] = [value]
            else:
                self[key].append(value)
        for key in self:
            if len(self[key]) == 1:
                self[key] = self[key][0]

    def extract_headers(self, header_name: str):
        """Returns all headers with name == header_name as list of tuples (name, value)"""
        if header_name.startswith("grpc-"):
            return ()
        else:
            value = self.pop(header_name)
            is_binary = header_name.endswith("-bin")

            if not isinstance(value, list):
                value_list = [value]
            else:
                value_list = value

            if is_binary:
                return ((header_name, b64decode(value)) for value_sublist in value_list for value
                        in value_sublist.split(","))
            else:
                return ((header_name, value) for value in value_list)


def sanitize_headers(headers):
    for name, value in headers:
        if isinstance(value, bytes) and not name.endswith("-bin"):
            raise ValueError("Got binary value for header name '{}', but name does not end "
                             "with '-bin' suffix".format(name))
        if name.startswith("grpc-"):
            raise ValueError("Got header with name '{}', but custom metadata headers should "
                             "not start with 'grpc-' prefix".format(name))
        if name.endswith("-bin"):
            yield name, b64encode(value)
        else:
            yield name, value


def b64decode(data: str) -> bytes:
    # Apply missing padding
    missing_padding = len(data) % 4
    if missing_padding:
        data += "=" * (4 - missing_padding)
    return base64.b64decode(data)


def b64encode(data: bytes) -> str:
    return base64.b64encode(data).rstrip(b"=").decode("utf-8")
