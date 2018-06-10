import unittest
import curio
import grpc
import typing
import time
from .greeter_pb2 import HelloReply, HelloRequest
from .greeter_pb2_grpc import GreeterStub, GreeterServicer, add_GreeterServicer_to_server
from purerpc import *
from .test_case_base import PureRPCTestCase


class TestStatusCodes(PureRPCTestCase):
    def test_purerpc_server_grpc_client_wrong_service_name(self):
        service = Service("some_package.SomeWrongServiceName")

        @service.rpc("SayHello")
        async def say_hello(message: HelloRequest) -> HelloReply:
            return HelloReply(message=f"Hello, {message.name}")

        with self.run_purerpc_service_in_process(service) as port:
            with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                stub = GreeterStub(channel)
                with self.assertRaisesRegex(grpc._channel._Rendezvous, r"not implemented"):
                    stub.SayHello(HelloRequest(name="World"))

    def test_purerpc_server_grpc_client_wrong_method_name(self):
        service = Service("Greeter")

        @service.rpc("SomeOtherMethod")
        async def say_hello(message: HelloRequest) -> HelloReply:
            return HelloReply(message=f"Hello, {message.name}")

        with self.run_purerpc_service_in_process(service) as port:
            with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                stub = GreeterStub(channel)
                with self.assertRaisesRegex(grpc._channel._Rendezvous, r"not implemented"):
                    stub.SayHello(HelloRequest(name="World"))

    def test_grpc_server_purerpc_client_wrong_method_name(self):
        class Servicer(GreeterServicer):
            def SayHelloGoodbye(self, message, context):
                yield HelloReply(message=f"Hello, {message.name}")
                time.sleep(0.05)
                yield HelloReply(message=f"Goodbye, {message.name}")

        with self.run_grpc_service_in_process(
                        lambda server: add_GreeterServicer_to_server(Servicer(), server)) as port, \
             self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):
            
            GreeterStub = grpc_module.GreeterStub
            async def main():
                channel = Channel("localhost", port)
                await channel.connect()
                stub = GreeterStub(channel)
                with self.assertRaises(UnimplementedError):
                    await stub.SayHello(HelloRequest(name="World"))
            curio.run(main)

    def test_purerpc_server_grpc_client_status_codes(self):
        def test(error_to_raise, regex_to_check):
            service = Service("Greeter")

            @service.rpc("SayHello")
            async def say_hello(message: HelloRequest) -> HelloReply:
                raise error_to_raise

            with self.run_purerpc_service_in_process(service) as port:
                with grpc.insecure_channel('127.0.0.1:{}'.format(port)) as channel:
                    stub = GreeterStub(channel)
                    with self.assertRaisesRegex(grpc._channel._Rendezvous, regex_to_check):
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


    def test_purerpc_server_purerpc_client_status_codes(self):
        def test(error_to_raise, regex_to_check):
            service = Service("Greeter")

            @service.rpc("SayHello")
            async def say_hello(message: HelloRequest) -> HelloReply:
                raise error_to_raise

            with self.run_purerpc_service_in_process(service) as port, \
                 self.compile_temp_proto("data/greeter.proto") as (_, grpc_module):

                GreeterStub = grpc_module.GreeterStub
                async def main():
                    channel = Channel("localhost", port)
                    await channel.connect()
                    stub = GreeterStub(channel)
                    with self.assertRaises(error_to_raise):
                        await stub.SayHello(HelloRequest(name="World"))
                curio.run(main)

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
