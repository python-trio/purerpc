import os
import sys
import autopep8
from collections import defaultdict

from google.protobuf.compiler.plugin_pb2 import CodeGeneratorRequest
from google.protobuf.compiler.plugin_pb2 import CodeGeneratorResponse
from google.protobuf import descriptor_pb2
from purerpc.rpc import Cardinality

IMPORT_STRINGS = """import purerpc.server
import purerpc.client
from purerpc.rpc import Cardinality, RPCSignature
"""


def get_python_package(proto_name):
    package_name = proto_name[:-len(".proto")]
    return package_name.replace("/", ".") + "_pb2"


def simple_type(type_):
    simple_type = type_.split(".")[-1]
    return simple_type


def get_python_type(proto_name, proto_type):
    print(proto_name, proto_type, file=sys.stderr)
    if proto_type.startswith("."):
        return get_python_package(proto_name) + "." + simple_type(proto_type)
    else:
        return proto_type


def get_proto(entity_name, imports, named_entities, current_proto):
    simple_name = simple_type(entity_name)
    for import_ in imports:
        if simple_name in named_entities[import_]:
            return import_
    return current_proto


def generate_single_proto(proto_file: descriptor_pb2.FileDescriptorProto,
                          named_entities):
    contents = IMPORT_STRINGS
    contents += "import {}\n".format(get_python_package(proto_file.name))
    for dep_module in proto_file.dependency:
        contents += "import {}\n".format(get_python_package(dep_module))
    for service in proto_file.service:
        contents += "\n\nclass {}Servicer(purerpc.server.Servicer):\n".format(service.name)
        for method in service.method:
            contents += "    async def {}(self, input_message{}):\n".format(
                method.name, "s" if method.client_streaming else "")
            contents += "        raise NotImplementedError()\n\n"
        contents += "    @property\n"
        contents += "    def service(self) -> purerpc.server.Service:\n"
        contents += "        service_obj = purerpc.server.Service(\"{}\")\n".format(service.name)
        for method in service.method:
            cardinality = Cardinality.get_cardinality_for(request_stream=method.client_streaming,
                                                          response_stream=method.server_streaming)
            contents += ("        service_obj.add_method(\"{}\", self.{}, "
                         "RPCSignature({}, {}, {}))\n".format(
                             method.name, method.name, cardinality,
                             get_python_type(get_proto(method.input_type, proto_file.dependency,
                                                       named_entities, proto_file.name),
                                             method.input_type),
                             get_python_type(get_proto(method.output_type, proto_file.dependency,
                                                       named_entities, proto_file.name),
                                             method.output_type)))
        contents += "        return service_obj\n\n\n"

        contents += "class {}Stub:\n".format(service.name)
        contents += "    def __init__(self, channel):\n"
        contents += "        self._client = purerpc.client.Client(\"{}\", channel)\n".format(
            service.name)
        for method in service.method:
            cardinality = Cardinality.get_cardinality_for(request_stream=method.client_streaming,
                                                          response_stream=method.server_streaming)
            contents += ("        self.{} = self._client.get_method_stub("
                         "\"{}\", RPCSignature({}, {}, {}))\n".format(
                             method.name, method.name, cardinality,
                             get_python_type(get_proto(method.input_type, proto_file.dependency,
                                                       named_entities, proto_file.name),
                                             method.input_type),
                             get_python_type(get_proto(method.output_type, proto_file.dependency,
                                                       named_entities, proto_file.name),
                                             method.output_type)))
        contents += "\n\n"

    return autopep8.fix_code(contents, options={"experimental": True, "max_line_length": 100})


def main():
    request = CodeGeneratorRequest.FromString(sys.stdin.buffer.read())

    files_to_generate = set(request.file_to_generate)

    response = CodeGeneratorResponse()
    named_entities = defaultdict(set)
    for proto_file in request.proto_file:
        for message in proto_file.message_type:
            named_entities[proto_file.name].add(message.name)
        for enum in proto_file.enum_type:
            named_entities[proto_file.name].add(enum.name)
        for service in proto_file.service:
            named_entities[proto_file.name].add(service.name)
        for extension in proto_file.extension:
            named_entities[proto_file.name].add(extension.name)
    for proto_file in request.proto_file:
        if proto_file.name in files_to_generate:
            out = response.file.add()
            out.name = proto_file.name.replace('.proto', "_grpc.py")
            out.content = generate_single_proto(proto_file, named_entities)

    sys.stdout.buffer.write(response.SerializeToString())
