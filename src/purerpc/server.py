import sys
import inspect
import collections
import functools

import logging
from contextlib import asynccontextmanager, AsyncExitStack

import anyio
import anyio.abc
from anyio import TASK_STATUS_IGNORED
from anyio.streams.tls import TLSListener

from .grpclib.events import RequestReceived
from .grpclib.status import Status, StatusCode
from .grpclib.exceptions import RpcFailedError
from .utils import run as purerpc_run
from purerpc.grpc_proto import GRPCProtoStream, GRPCProtoSocket
from purerpc.rpc import RPCSignature, Cardinality
from purerpc.wrappers import call_server_unary_unary, \
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


@asynccontextmanager
async def _service_wrapper(service=None, setup_fn=None, teardown_fn=None):
    if setup_fn is not None:
        yield await setup_fn()
    else:
        yield service

    if teardown_fn is not None:
        await teardown_fn()


class Server:
    def __init__(self, port=50055, ssl_context=None):
        self.port = port
        self._ssl_context = ssl_context
        self.services = {}
        self._connection_count = 0
        self._exception_count = 0

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

    async def serve_async(self, *, task_status=TASK_STATUS_IGNORED):
        """Run the grpc server

        The task_status protocol lets the caller know when the server is
        listening, and yields the port number (same given to Server constructor).
        """

        # TODO: resource usage warning
        async with AsyncExitStack() as stack:
            tcp_server = await anyio.create_tcp_listener(local_port=self.port, reuse_port=True)
            # read the resulting port, in case it was 0
            self.port = tcp_server.extra(anyio.abc.SocketAttribute.local_port)
            if self._ssl_context:
                tcp_server = TLSListener(tcp_server, self._ssl_context,
                                         standard_compatible=False)
            task_status.started(self.port)

            services_dict = {}
            for key, value in self.services.items():
                services_dict[key] = await stack.enter_async_context(value)

            await tcp_server.serve(ConnectionHandler(services_dict, self))

    def serve(self, backend=None):
        """
        DEPRECATED - use serve_async() instead

        This function runs an entire async event loop (there can only be one
        per thread), and there is no way to know when the server is ready for
        connections.
        """
        purerpc_run(self.serve_async, backend=backend)


class ConnectionHandler:
    RECEIVE_BUFFER_SIZE = 65536

    def __init__(self, services: dict, server: Server):
        self.config = GRPCConfiguration(client_side=False)
        self.services = services
        self._server = server

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
                # TODO: limit catch to Exception, so async cancel can propagate
                log.warning("Got exception while writing response stream",
                            exc_info=log.getEffectiveLevel() == logging.DEBUG)
                await stream.close(Status(StatusCode.CANCELLED, status_message=repr(sys.exc_info())))
        except:
            # TODO: limit catch to Exception, so async cancel can propagate
            log.warning("Got exception in request_received",
                        exc_info=log.getEffectiveLevel() == logging.DEBUG)

    async def __call__(self, stream_: anyio.abc.SocketStream):
        # TODO: Should at least pass through GeneratorExit
        self._server._connection_count += 1
        try:
            async with GRPCProtoSocket(self.config, stream_) as grpc_socket:
                # TODO: resource usage warning
                # TODO: TaskGroup() uses a lot of memory if the connection is kept for a long time
                # TODO: do we really need it here?
                async with anyio.create_task_group() as task_group:
                    async for stream in grpc_socket.listen():
                        task_group.start_soon(self.request_received, stream)
        except:
            # TODO: limit catch to Exception, so async cancel can propagate
            # TODO: migrate off this broad catching of exceptions.  The library
            #  user should decide the policy.
            log.warning("Got exception in main dispatch loop",
                        exc_info=log.getEffectiveLevel() == logging.DEBUG)
            self._server._exception_count += 1
