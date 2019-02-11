import functools
import time

import anyio
import grpc
import pytest

from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server
from purerpc import *
from purerpc.test_utils import run_purerpc_service_in_process, run_grpc_service_in_process


def test_purerpc_server_grpc_client_wrong_service_name():
    service = Service("some_package.SomeWrongServiceName")

    @service.rpc("SayHello")
    async def say_hello(message: HelloRequest) -> HelloReply:
        return HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(service) as port:
        with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
            stub = GreeterStub(channel)
            with pytest.raises(grpc._channel._Rendezvous, match=r"not implemented"):
                stub.SayHello(HelloRequest(name="World"))


def test_purerpc_server_grpc_client_wrong_method_name():
    service = Service("Greeter")

    @service.rpc("SomeOtherMethod")
    async def say_hello(message: HelloRequest) -> HelloReply:
        return HelloReply(message="Hello, " + message.name)

    with run_purerpc_service_in_process(service) as port:
        with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
            stub = GreeterStub(channel)
            with pytest.raises(grpc._channel._Rendezvous, match=r"not implemented"):
                stub.SayHello(HelloRequest(name="World"))


def test_grpc_server_purerpc_client_wrong_method_name(greeter_grpc):
    class Servicer(GreeterServicer):
        def SayHelloGoodbye(self, message, context):
            yield HelloReply(message="Hello, " + message.name)
            time.sleep(0.05)
            yield HelloReply(message="Goodbye, " + message.name)

    with run_grpc_service_in_process(functools.partial(add_GreeterServicer_to_server, Servicer())) as port:
        GreeterStub = greeter_grpc.GreeterStub
        async def main():
            async with insecure_channel("localhost", port) as channel:
                stub = GreeterStub(channel)
                with pytest.raises(UnimplementedError):
                    await stub.SayHello(HelloRequest(name="World"))
        anyio.run(main)


def test_purerpc_server_grpc_client_status_codes():
    def test(error_to_raise, regex_to_check):
        service = Service("Greeter")

        @service.rpc("SayHello")
        async def say_hello(message: HelloRequest) -> HelloReply:
            raise error_to_raise

        with run_purerpc_service_in_process(service) as port:
            with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                stub = GreeterStub(channel)
                with pytest.raises(grpc._channel._Rendezvous, match=regex_to_check):
                    stub.SayHello(HelloRequest(name="World"))

    test(CancelledError, "CANCELLED")
    test(UnknownError, "UNKNOWN")
    test(InvalidArgumentError, "INVALID_ARGUMENT")
    test(DeadlineExceededError, "DEADLINE_EXCEEDED")
    test(NotFoundError, "NOT_FOUND")
    test(AlreadyExistsError, "ALREADY_EXISTS")
    test(PermissionDeniedError, "PERMISSION_DENIED")
    test(ResourceExhaustedError, "RESOURCE_EXHAUSTED")
    test(FailedPreconditionError, "FAILED_PRECONDITION")
    test(AbortedError, "ABORTED")
    test(OutOfRangeError, "OUT_OF_RANGE")
    test(UnimplementedError, "UNIMPLEMENTED")
    test(InternalError, "INTERNAL")
    test(UnavailableError, "UNAVAILABLE")
    test(DataLossError, "DATA_LOSS")
    test(UnauthenticatedError, "UNAUTHENTICATED")


def test_purerpc_server_purerpc_client_status_codes(greeter_grpc):
    def test(error_to_raise, regex_to_check):
        service = Service("Greeter")

        @service.rpc("SayHello")
        async def say_hello(message: HelloRequest) -> HelloReply:
            raise error_to_raise

        with run_purerpc_service_in_process(service) as port:
            GreeterStub = greeter_grpc.GreeterStub
            async def main():
                async with insecure_channel("localhost", port) as channel:
                    stub = GreeterStub(channel)
                    with pytest.raises(error_to_raise, match=regex_to_check):
                        await stub.SayHello(HelloRequest(name="World"))
            anyio.run(main)

    test(CancelledError, "CANCELLED")
    test(UnknownError, "UNKNOWN")
    test(InvalidArgumentError, "INVALID_ARGUMENT")
    test(DeadlineExceededError, "DEADLINE_EXCEEDED")
    test(NotFoundError, "NOT_FOUND")
    test(AlreadyExistsError, "ALREADY_EXISTS")
    test(PermissionDeniedError, "PERMISSION_DENIED")
    test(ResourceExhaustedError, "RESOURCE_EXHAUSTED")
    test(FailedPreconditionError, "FAILED_PRECONDITION")
    test(AbortedError, "ABORTED")
    test(OutOfRangeError, "OUT_OF_RANGE")
    test(UnimplementedError, "UNIMPLEMENTED")
    test(InternalError, "INTERNAL")
    test(UnavailableError, "UNAVAILABLE")
    test(DataLossError, "DATA_LOSS")
    test(UnauthenticatedError, "UNAUTHENTICATED")
