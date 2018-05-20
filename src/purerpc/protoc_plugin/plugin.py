import os
import sys
import autopep8

from google.protobuf.compiler.plugin_pb2 import CodeGeneratorRequest
from google.protobuf.compiler.plugin_pb2 import CodeGeneratorResponse
from google.protobuf import descriptor_pb2

IMPORT_STRINGS = """import purerpc.server
from async_generator import async_generator
"""


def get_cardinality_string(is_streaming):
    return "stream" if is_streaming else "unary"


def get_python_package(proto_name):
    package_name = proto_name[:-len(".proto")]
    return package_name.replace("/", ".") + "_pb2"


def get_python_type(proto_name, proto_type):
    if proto_type.startswith("."):
        return get_python_package(proto_name) + proto_type
    else:
        return proto_type


def generate_single_proto(proto_file: descriptor_pb2.FileDescriptorProto):
    contents = IMPORT_STRINGS
    contents += "import {}\n".format(get_python_package(proto_file.name))
    for dep_module in proto_file.dependency:
        contents += "import {}\n".format(get_python_package(dep_module))
    for service in proto_file.service:
        contents += "\n\nclass {}Servicer(purerpc.server.Servicer):\n".format(service.name)
        for method in service.method:
            if method.server_streaming:
                contents += "    @async_generator\n"
            contents += "    async def {}(self, input_message{}):\n".format(method.name,
                                                                    "s" if
                                                                    method.client_streaming else "")
            contents += "        raise NotImplementedError()\n\n"
        contents += "    @property\n"
        contents += "    def service(self) -> purerpc.server.Service:\n"
        contents += "        service_obj = purerpc.server.Service(\"{}\")\n".format(service.name)
        for method in service.method:
            service_method_name = "_".join([
                "add",
                get_cardinality_string(method.client_streaming),
                get_cardinality_string(method.server_streaming)
            ])
            contents += "        service_obj.{}(\"{}\", self.{}, {}, {})\n".format(
                service_method_name, method.name, method.name,
                get_python_type(proto_file.name, method.input_type),
                get_python_type(proto_file.name, method.output_type))
        contents += "        return service_obj\n"
    return autopep8.fix_code(contents, options={"experimental": True, "max_line_length": 100})


def main():
    request = CodeGeneratorRequest.FromString(sys.stdin.buffer.read())

    files_to_generate = set(request.file_to_generate)

    response = CodeGeneratorResponse()
    for proto_file in request.proto_file:
        if proto_file.name in files_to_generate:
            out = response.file.add()
            out.name = proto_file.name.replace('.proto', "_grpc.py")
            out.content = generate_single_proto(proto_file)

    sys.stdout.buffer.write(response.SerializeToString())
