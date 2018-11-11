import sys
import inspect
import warnings
import collections
import functools
from multiprocessing import Process

import curio
import curio.meta
import typing
import logging

from .grpclib.events import RequestReceived
from .grpclib.status import Status, StatusCode
from .grpclib.exceptions import RpcFailedError
from purerpc.grpc_proto import GRPCProtoStream, GRPCProtoSocket
from purerpc.grpc_socket import GRPCSocket, GRPCStream
from purerpc.rpc import RPCSignature, Cardinality
from purerpc.utils import is_linux, get_linux_kernel_version
from purerpc.wrappers import stream_to_async_iterator, call_server_unary_unary, \
    call_server_unary_stream, call_server_stream_unary, call_server_stream_stream

from .grpclib.connection import GRPCConfiguration


BoundRPCMethod = collections.namedtuple("BoundRPCMethod", ["method_fn", "signature"])


class Service:
    def __init__(self, name):
        self.name = name
        self.methods = {}

    def add_method(self, method_name: str, method_fn, rpc_signature: RPCSignature,
                   method_signature: inspect.Signature = None):
        if method_signature is None:
            method_signature = inspect.signature(method_fn)
        if len(method_signature.parameters) == 1:
            def method_fn_with_headers(arg, request):
                return method_fn(arg)
        elif len(method_signature.parameters) == 2:
            if list(method_signature.parameters.values())[1].name == "request":
                method_fn_with_headers = method_fn
            else:
                raise ValueError("Expected second parameter 'request'")
        else:
            raise ValueError("Expected method_fn to have exactly one or two parameters")
        self.methods[method_name] = BoundRPCMethod(method_fn_with_headers, rpc_signature)

    def rpc(self, method_name):
        def decorator(func):
            signature = inspect.signature(func)
            if signature.return_annotation == signature.empty:
                raise ValueError("Only annotated methods can be used with Service.rpc() decorator")
            if len(signature.parameters) not in (1, 2):
                raise ValueError("Only functions with one or two parameters can be used with "
                                 "Service.rpc() decorator")
            parameter = next(iter(signature.parameters.values()))
            if parameter.annotation == parameter.empty:
                raise ValueError("Only annotated methods can be used with Service.rpc() decorator")

            rpc_signature = RPCSignature.from_annotations(parameter.annotation,
                                                          signature.return_annotation)
            self.add_method(method_name, func, rpc_signature, method_signature=signature)
            return func
        return decorator


class Servicer:
    @property
    def service(self) -> Service:
        raise NotImplementedError()


class Server:
    def __init__(self, port=50055, num_processes=1):
        self.port = port
        self.services = {}
        self.num_processes = num_processes
        if num_processes > 1 and (not is_linux() or get_linux_kernel_version() < (3, 9)):
            warnings.warn("Selected num_processes > 1 and not running Linux kernel >= 3.9")

    def add_service(self, service):
        self.services[service.name] = service

    def _create_socket_and_listen(self):
        return curio.tcp_server_socket('', self.port, reuse_address=True, reuse_port=True)

    async def _run_async_server(self, socket):
        await curio.network.run_server(socket, lambda c, a: ConnectionHandler(self)(c, a))

    def _target_fn(self):
        socket = self._create_socket_and_listen()
        curio.run(self._run_async_server, socket)

    def serve(self):
        if self.num_processes == 1:
            self._target_fn()
        else:
            # this is simple SO_REUSEPORT load balancing on Linux
            processes = []
            for i in range(self.num_processes):
                process = Process(target=self._target_fn)
                process.start()
                processes.append(process)
            for process in processes:
                process.join()


class ConnectionHandler:
    RECEIVE_BUFFER_SIZE = 65536

    def __init__(self, server: Server):
        self.config = GRPCConfiguration(client_side=False)
        self.grpc_socket = None
        self.server = server

    async def request_received(self, stream: GRPCProtoStream):
        await stream.start_response()
        event = await stream.receive_event()

        if not isinstance(event, RequestReceived):
            await stream.close(Status(StatusCode.INTERNAL, status_message="Expected headers"))
            return

        try:
            service = self.server.services[event.service_name]
        except KeyError:
            await stream.close(Status(
                StatusCode.UNIMPLEMENTED,
                status_message=f"Service {event.service_name} is not implemented"
            ))
            return

        try:
            bound_rpc_method = service.methods[event.method_name]
        except KeyError:
            await stream.close(Status(
                StatusCode.UNIMPLEMENTED,
                status_message=f"Method {event.method_name} is not implemented in "
                               f"service {event.service_name}"
            ))
            return

        # TODO: Should at least pass through GeneratorExit
        try:
            method_fn = functools.partial(bound_rpc_method.method_fn, request=event)
            cardinality = bound_rpc_method.signature.cardinality
            stream.expect_message_type(bound_rpc_method.signature.request_type)
            if cardinality == Cardinality.STREAM_STREAM:
                await call_server_stream_stream(method_fn, stream)
            elif cardinality == Cardinality.UNARY_STREAM:
                await call_server_unary_stream(method_fn, stream)
            elif cardinality == Cardinality.STREAM_UNARY:
                await call_server_stream_unary(method_fn, stream)
            else:
                await call_server_unary_unary(method_fn, stream)
        except RpcFailedError as error:
            await stream.close(error.status)
        except:
            logging.exception("Got exception while writing response stream")
            await stream.close(Status(StatusCode.CANCELLED, status_message=repr(sys.exc_info())))

    async def __call__(self, socket, addr):
        self.grpc_socket = GRPCProtoSocket(self.config, socket)
        await self.grpc_socket.initiate_connection()

        # TODO: TaskGroup() uses a lot of memory if the connection is kept for a long time
        # TODO: do we really need it here?
        # task_group = curio.TaskGroup()
        # TODO: Should at least pass through GeneratorExit
        try:
            async for stream in self.grpc_socket.listen():
                await curio.spawn(self.request_received(stream), daemon=True)
        except:
            logging.exception("Got exception in main dispatch loop")
        finally:
            # await task_group.join()
            # await self.grpc_socket.shutdown()
            pass
