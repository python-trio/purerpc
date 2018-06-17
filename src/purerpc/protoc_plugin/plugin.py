import os
import sys
import itertools

from google.protobuf.compiler.plugin_pb2 import CodeGeneratorRequest
from google.protobuf.compiler.plugin_pb2 import CodeGeneratorResponse
from google.protobuf import descriptor_pb2
from purerpc import Cardinality


def get_python_package(proto_name):
    package_name = proto_name[:-len(".proto")]
    return package_name.replace("/", ".") + "_pb2"


def simple_type(type_):
    simple_type = type_.split(".")[-1]
    return simple_type


def get_python_type(proto_name, proto_type):
    if proto_type.startswith("."):
        return get_python_package(proto_name) + "." + simple_type(proto_type)
    else:
        return proto_type


def generate_single_proto(proto_file: descriptor_pb2.FileDescriptorProto,
                          proto_for_entity):
    lines = ["import purerpc"]
    lines.append(f"import {get_python_package(proto_file.name)}")
    for dep_module in proto_file.dependency:
        lines.append(f"import {get_python_package(dep_module)}")
    for service in proto_file.service:
        if proto_file.package:
            fully_qualified_service_name = proto_file.package + "." + service.name
        else:
            fully_qualified_service_name = service.name

        lines.append(f"\n\nclass {service.name}Servicer(purerpc.Servicer):")
        for method in service.method:
            plural_suffix = "s" if method.client_streaming else ""
            lines.append(f"    async def {method.name}(self, input_message{plural_suffix}):")
            lines.append("        raise NotImplementedError()\n")
        lines.append("    @property")
        lines.append("    def service(self) -> purerpc.Service:")
        lines.append("        service_obj = purerpc.Service(")
        lines.append(f"            \"{fully_qualified_service_name}\"")
        lines.append("        )")
        for method in service.method:
            input_proto = proto_for_entity[method.input_type]
            output_proto = proto_for_entity[method.output_type]
            cardinality = Cardinality.get_cardinality_for(request_stream=method.client_streaming,
                                                          response_stream=method.server_streaming)
            lines.append("        service_obj.add_method(")
            lines.append(f"            \"{method.name}\",")
            lines.append(f"            self.{method.name},")
            lines.append("            purerpc.RPCSignature(")
            lines.append(f"                purerpc.{cardinality},")
            lines.append(f"                {get_python_type(input_proto, method.input_type)},")
            lines.append(f"                {get_python_type(output_proto, method.output_type)},")
            lines.append("            )")
            lines.append("        )")
        lines.append("        return service_obj\n\n")

        lines.append(f"class {service.name}Stub:")
        lines.append("    def __init__(self, channel):")
        lines.append("        self._client = purerpc.Client(")
        lines.append(f"            \"{fully_qualified_service_name}\",")
        lines.append("            channel")
        lines.append("        )")
        for method in service.method:
            input_proto = proto_for_entity[method.input_type]
            output_proto = proto_for_entity[method.output_type]
            cardinality = Cardinality.get_cardinality_for(request_stream=method.client_streaming,
                                                          response_stream=method.server_streaming)
            lines.append(f"        self.{method.name} = self._client.get_method_stub(")
            lines.append(f"            \"{method.name}\",")
            lines.append("            purerpc.RPCSignature(")
            lines.append(f"                purerpc.{cardinality},")
            lines.append(f"                {get_python_type(input_proto, method.input_type)},")
            lines.append(f"                {get_python_type(output_proto, method.output_type)},")
            lines.append("            )")
            lines.append("        )")

    return "\n".join(lines)


def main():
    request = CodeGeneratorRequest.FromString(sys.stdin.buffer.read())

    files_to_generate = set(request.file_to_generate)

    response = CodeGeneratorResponse()
    proto_for_entity = dict()
    for proto_file in request.proto_file:
        package_name = proto_file.package
        for named_entity in itertools.chain(proto_file.message_type, proto_file.enum_type,
                                            proto_file.service, proto_file.extension):
            if package_name:
                fully_qualified_name = ".".join(["", package_name, named_entity.name])
            else:
                fully_qualified_name = "." + named_entity.name
            proto_for_entity[fully_qualified_name] = proto_file.name
    for proto_file in request.proto_file:
        if proto_file.name in files_to_generate:
            out = response.file.add()
            out.name = proto_file.name.replace('.proto', "_grpc.py")
            out.content = generate_single_proto(proto_file, proto_for_entity)
    sys.stdout.buffer.write(response.SerializeToString())
