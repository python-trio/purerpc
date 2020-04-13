import sys
import inspect
import socket
import collections
import functools
import async_exit_stack
import logging

import anyio
from async_generator import async_generator, asynccontextmanager, yield_

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

log = logging.getLogger(__name__)

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


def tcp_server_socket(host, port, family=socket.AF_INET, backlog=100,
                      reuse_address=True, reuse_port=False, ssl_context=None):
    raw_socket = socket.socket(family, socket.SOCK_STREAM)
    try:
        if reuse_address:
            raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

        if reuse_port:
            try:
                raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
            except (AttributeError, OSError) as e:
                log.warning('reuse_port=True option failed', exc_info=True)

        raw_socket.bind((host, port))
        raw_socket.listen(backlog)
    except Exception:
        raw_socket.close()
        raise

    return raw_socket


@asynccontextmanager
@async_generator
async def _service_wrapper(service=None, setup_fn=None, teardown_fn=None):
    if setup_fn is not None:
        await yield_(await setup_fn())
    else:
        await yield_(service)

    if teardown_fn is not None:
        await teardown_fn()


class Server:
    def __init__(self, port=50055, ssl_context=None):
        self.port = port
        self._ssl = ssl_context
        self.services = {}

    def add_service(self, service=None, context_manager=None, setup_fn=None, teardown_fn=None, name=None):
        if (service is not None) + (context_manager is not None) + (setup_fn is not None) != 1:
            raise ValueError("Precisely one of service, context_manager or setup_fn should be set")
        if name is None:
            if hasattr(service, "name"):
                name = service.name
            elif hasattr(context_manager, "name"):
                name = context_manager.name
            elif hasattr(setup_fn, "name"):
                name = setup_fn.name
            else:
                raise ValueError("Could not infer name, please provide 'name' argument to this function call "
                                 "or define 'name' attribute on service, context_manager or setup_fn")
        if service is not None:
            self.services[name] = _service_wrapper(service=service)
        elif context_manager is not None:
            self.services[name] = context_manager
        elif setup_fn is not None:
            self.services[name] = _service_wrapper(setup_fn=setup_fn, teardown_fn=teardown_fn)
        else:
            raise ValueError("Shouldn't have happened")

    def _create_socket_and_listen(self):
        return tcp_server_socket('', self.port, reuse_address=True, reuse_port=True)

    async def _run_async_server(self, raw_socket):
        socket = anyio._get_asynclib().Socket(raw_socket)

        # TODO: resource usage warning
        async with async_exit_stack.AsyncExitStack() as stack:
            tcp_server = await stack.enter_async_context(
                anyio._networking.SocketStreamServer(socket,
                                                     self._ssl,
                                                     self._ssl is not None, 
                                                     False)
            )
            task_group = await stack.enter_async_context(anyio.create_task_group())

            services_dict = {}
            for key, value in self.services.items():
                services_dict[key] = await stack.enter_async_context(value)

            async for socket in tcp_server.accept_connections():
                await task_group.spawn(ConnectionHandler(services_dict), socket)

    def _target_fn(self, backend):
        socket = self._create_socket_and_listen()
        anyio.run(self._run_async_server, socket, backend=backend)

    def serve(self, backend=None):
        self._target_fn(backend)


class ConnectionHandler:
    RECEIVE_BUFFER_SIZE = 65536

    def __init__(self, services: dict):
        self.config = GRPCConfiguration(client_side=False)
        self.grpc_socket = None
        self.services = services

    async def request_received(self, stream: GRPCProtoStream):
        try:
            await stream.start_response()
            event = await stream.receive_event()

            if not isinstance(event, RequestReceived):
                await stream.close(Status(StatusCode.INTERNAL, status_message="Expected headers"))
                return

            try:
                service = self.services[event.service_name]
            except KeyError:
                await stream.close(Status(
                    StatusCode.UNIMPLEMENTED,
                    status_message="Service {service_name} is not implemented".format(service_name=event.service_name)
                ))
                return

            try:
                bound_rpc_method = service.methods[event.method_name]
            except KeyError:
                await stream.close(Status(
                    StatusCode.UNIMPLEMENTED,
                    status_message="Method {method_name} is not implemented in service {service_name}".format(
                        method_name=event.method_name,
                        service_name=event.service_name
                    )
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
                log.warning("Got exception while writing response stream",
                            exc_info=log.getEffectiveLevel() == logging.DEBUG)
                await stream.close(Status(StatusCode.CANCELLED, status_message=repr(sys.exc_info())))
        except:
            log.warning("Got exception in request_received",
                        exc_info=log.getEffectiveLevel() == logging.DEBUG)

    async def __call__(self, socket):
        # TODO: Should at least pass through GeneratorExit
        try:
            async with GRPCProtoSocket(self.config, socket) as self.grpc_socket:
                # TODO: resource usage warning
                # TODO: TaskGroup() uses a lot of memory if the connection is kept for a long time
                # TODO: do we really need it here?
                async with anyio.create_task_group() as task_group:
                    async for stream in self.grpc_socket.listen():
                        await task_group.spawn(self.request_received, stream)
        except:
            log.warning("Got exception in main dispatch loop",
                        exc_info=log.getEffectiveLevel() == logging.DEBUG)
