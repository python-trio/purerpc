import os
import sys

from google.protobuf.compiler.plugin_pb2 import CodeGeneratorRequest
from google.protobuf.compiler.plugin_pb2 import CodeGeneratorResponse


def main():
    with os.fdopen(sys.stdin.fileno(), 'rb') as inp:
        request = CodeGeneratorRequest.FromString(inp.read())

    print(request.proto_file, file=sys.stderr)

    response = CodeGeneratorResponse()
    for file_to_generate in request.file_to_generate:
        print(file_to_generate, file=sys.stderr)

        out = response.file.add()
        out.name = file_to_generate.replace('.proto', "_grpc.py")
        out.content = 'hello_world'

    sys.stdout.buffer.write(response.SerializeToString())
