import sys
import itertools

from google.protobuf.compiler.plugin_pb2 import CodeGeneratorRequest
from google.protobuf.compiler.plugin_pb2 import CodeGeneratorResponse
from google.protobuf import descriptor_pb2
from purerpc import Cardinality


def generate_import_statement(proto_name):
    module_path = proto_name[:-len(".proto")].replace("-", "_").replace("/", ".") + "_pb2"
    alias = get_python_module_alias(proto_name)
    return "import " + module_path + " as " + alias


def get_python_module_alias(proto_name):
    package_name = proto_name[:-len(".proto")]
    return package_name.replace("/", "_dot_").replace("-", "_") + "__pb2"


def simple_type(type_):
    simple_type = type_.split(".")[-1]
    return simple_type


def get_python_type(proto_name, proto_type):
    if proto_type.startswith("."):
        return get_python_module_alias(proto_name) + "." + simple_type(proto_type)
    else:
        return proto_type


def generate_single_proto(proto_file: descriptor_pb2.FileDescriptorProto,
                          proto_for_entity):
    lines = ["import purerpc"]
    lines.append(generate_import_statement(proto_file.name))
    for dep_module in proto_file.dependency:
        lines.append(generate_import_statement(dep_module))
    for service in proto_file.service:
        if proto_file.package:
            fully_qualified_service_name = proto_file.package + "." + service.name
        else:
            fully_qualified_service_name = service.name

        lines.append("\n\nclass {service_name}Servicer(purerpc.Servicer):".format(service_name=service.name))
        for method in service.method:
            plural_suffix = "s" if method.client_streaming else ""
            fmt_string = ("    async def {method_name}(self, input_message{plural_suffix}):\n"
                          "        raise NotImplementedError()\n")
            lines.append(fmt_string.format(
                method_name=method.name,
                plural_suffix=plural_suffix,
            ))
        fmt_string = ("    @property\n"
                      "    def service(self) -> purerpc.Service:\n"
                      "        service_obj = purerpc.Service(\n"
                      "            \"{fully_qualified_service_name}\"\n"
                      "        )")
        lines.append(fmt_string.format(fully_qualified_service_name=fully_qualified_service_name))
        for method in service.method:
            input_proto = proto_for_entity[method.input_type]
            output_proto = proto_for_entity[method.output_type]
            cardinality = Cardinality.get_cardinality_for(request_stream=method.client_streaming,
                                                          response_stream=method.server_streaming)
            fmt_string = ("        service_obj.add_method(\n"
                          "            \"{method_name}\",\n"
                          "            self.{method_name},\n"
                          "            purerpc.RPCSignature(\n"
                          "                purerpc.{cardinality},\n"
                          "                {input_type},\n"
                          "                {output_type},\n"
                          "            )\n"
                          "        )")
            lines.append(fmt_string.format(
                method_name=method.name,
                cardinality=cardinality,
                input_type=get_python_type(input_proto, method.input_type),
                output_type=get_python_type(output_proto, method.output_type),
            ))
        lines.append("        return service_obj\n\n")

        fmt_string = ("class {service_name}Stub:\n"
                      "    def __init__(self, channel):\n"
                      "        self._client = purerpc.Client(\n"
                      "            \"{fully_qualified_service_name}\",\n"
                      "            channel\n"
                      "        )")
        lines.append(fmt_string.format(
            service_name=service.name,
            fully_qualified_service_name=fully_qualified_service_name
        ))
        for method in service.method:
            input_proto = proto_for_entity[method.input_type]
            output_proto = proto_for_entity[method.output_type]
            cardinality = Cardinality.get_cardinality_for(request_stream=method.client_streaming,
                                                          response_stream=method.server_streaming)
            fmt_string = ("        self.{method_name} = self._client.get_method_stub(\n"
                          "            \"{method_name}\",\n"
                          "            purerpc.RPCSignature(\n"
                          "                purerpc.{cardinality},\n"
                          "                {input_type},\n"
                          "                {output_type},\n"
                          "            )\n"
                          "        )")
            lines.append(fmt_string.format(
                method_name=method.name,
                cardinality=cardinality,
                input_type=get_python_type(input_proto, method.input_type),
                output_type=get_python_type(output_proto, method.output_type),
            ))

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
            out.name = proto_file.name.replace('-', "_").replace('.proto', "_grpc.py")
            out.content = generate_single_proto(proto_file, proto_for_entity)
    sys.stdout.buffer.write(response.SerializeToString())
