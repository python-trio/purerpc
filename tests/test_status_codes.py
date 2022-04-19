import functools
import pickle
import base64
import string
import re

import pytest

import purerpc
from purerpc.test_utils import run_purerpc_service_in_process, run_grpc_service_in_process, grpc_channel, \
    grpc_client_parallelize, purerpc_channel

pytestmark = pytest.mark.anyio


def regex_and(first, second):
    return re.compile(r"(?=.*{first})(?=.*{second}).*".format(first=re.escape(first), second=re.escape(second)),
                      flags=re.DOTALL)


STATUS_CODES = [
    (purerpc.CancelledError, "CANCELLED", "percent encoded message: %"),
    (purerpc.UnknownError, "UNKNOWN", "привет"),
    (purerpc.InvalidArgumentError, "INVALID_ARGUMENT", "\r\n"),
    (purerpc.DeadlineExceededError, "DEADLINE_EXCEEDED", string.printable),
    (purerpc.NotFoundError, "NOT_FOUND", "message:" + string.whitespace),
    (purerpc.AlreadyExistsError, "ALREADY_EXISTS", "detailed message"),
    (purerpc.PermissionDeniedError, "PERMISSION_DENIED", "detailed message"),
    (purerpc.ResourceExhaustedError, "RESOURCE_EXHAUSTED", "detailed message"),
    (purerpc.FailedPreconditionError, "FAILED_PRECONDITION", "detailed message"),
    (purerpc.AbortedError, "ABORTED", "detailed message"),
    (purerpc.OutOfRangeError, "OUT_OF_RANGE", "detailed message"),
    (purerpc.UnimplementedError, "UNIMPLEMENTED", "detailed message"),
    (purerpc.InternalError, "INTERNAL", "detailed message"),
    (purerpc.UnavailableError, "UNAVAILABLE", "detailed message"),
    (purerpc.DataLossError, "DATA_LOSS", "detailed message"),
    (purerpc.UnauthenticatedError, "UNAUTHENTICATED", "detailed message"),
]


@pytest.fixture(scope="module")
def purerpc_port(greeter_pb2):
    service = purerpc.Service("Greeter")

    @service.rpc("SayHello")
    async def say_hello(message: greeter_pb2.HelloRequest) -> greeter_pb2.HelloReply:
        status_code_tuple = pickle.loads(base64.b64decode(message.name))
        raise status_code_tuple[0](status_code_tuple[2])

    with run_purerpc_service_in_process(service) as port:
        yield port


@pytest.fixture(scope="module")
def grpc_port(greeter_pb2, greeter_pb2_grpc):
    class Servicer(greeter_pb2_grpc.GreeterServicer):
        def SayHello(self, message, context):
            import grpc
            status_code_tuple = pickle.loads(base64.b64decode(message.name))
            context.abort(getattr(grpc.StatusCode, status_code_tuple[1]), status_code_tuple[2])

    with run_grpc_service_in_process(functools.partial(
            greeter_pb2_grpc.add_GreeterServicer_to_server, Servicer())) as port:
        yield port


@pytest.fixture(scope="module",
                params=["purerpc_port", "grpc_port"])
def port(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def purerpc_server_wrong_service_name_port(greeter_pb2):
    service = purerpc.Service("some_package.SomeWrongServiceName")

    @service.rpc("SayHello")
    async def say_hello(message: greeter_pb2.HelloRequest) -> greeter_pb2.HelloReply:
        return greeter_pb2.HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(service) as port:
        yield port


@pytest.fixture
def purerpc_server_wrong_method_name_port(greeter_pb2):
    service = purerpc.Service("Greeter")

    @service.rpc("SomeOtherMethod")
    async def say_hello(message: greeter_pb2.HelloRequest) -> greeter_pb2.HelloReply:
        return greeter_pb2.HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(service) as port:
        yield port


@pytest.fixture
def grpc_empty_servicer_port(greeter_pb2_grpc):
    class Servicer(greeter_pb2_grpc.GreeterServicer):
        pass

    with run_grpc_service_in_process(functools.partial(
            greeter_pb2_grpc.add_GreeterServicer_to_server, Servicer())) as port:
        yield port


@grpc_client_parallelize(1)
@grpc_channel("purerpc_server_wrong_service_name_port")
def test_grpc_client_wrong_service_name(greeter_pb2, greeter_pb2_grpc, channel):
    stub = greeter_pb2_grpc.GreeterStub(channel)
    with pytest.raises(BaseException, match=r"not implemented"):
        stub.SayHello(greeter_pb2.HelloRequest(name="World"))


@grpc_client_parallelize(1)
@grpc_channel("purerpc_server_wrong_method_name_port")
def test_grpc_client_wrong_method_name(greeter_pb2, greeter_pb2_grpc, channel):
    stub = greeter_pb2_grpc.GreeterStub(channel)
    with pytest.raises(BaseException, match=r"not implemented"):
        stub.SayHello(greeter_pb2.HelloRequest(name="World"))

@purerpc_channel("grpc_empty_servicer_port")
async def test_purerpc_client_empty_servicer(greeter_pb2, greeter_grpc, channel):
    stub = greeter_grpc.GreeterStub(channel)
    with pytest.raises(purerpc.UnimplementedError):
        await stub.SayHello(greeter_pb2.HelloRequest(name="World"))


@pytest.mark.parametrize("status_code_tuple", STATUS_CODES)
@grpc_client_parallelize(1)
@grpc_channel("purerpc_port")
def test_grpc_client_status_codes(status_code_tuple, greeter_pb2, greeter_pb2_grpc, channel):
    stub = greeter_pb2_grpc.GreeterStub(channel)
    with pytest.raises(BaseException, match=regex_and(status_code_tuple[1], status_code_tuple[2])):
        stub.SayHello(greeter_pb2.HelloRequest(name=base64.b64encode(pickle.dumps(status_code_tuple))))


@pytest.mark.parametrize("status_code_tuple", STATUS_CODES)
@purerpc_channel("port")
async def test_purerpc_client_status_codes(status_code_tuple, greeter_pb2, greeter_grpc, channel):
    purerpc_exception = status_code_tuple[0]
    stub = greeter_grpc.GreeterStub(channel)
    with pytest.raises(purerpc_exception, match=regex_and(status_code_tuple[1], status_code_tuple[2])):
        await stub.SayHello(greeter_pb2.HelloRequest(name=base64.b64encode(pickle.dumps(status_code_tuple))))
