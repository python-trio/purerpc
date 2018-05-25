import collections
import sys
import inspect
import warnings
from multiprocessing import Process

import pdb
import curio
import objgraph
import typing
import logging

from purerpc.grpc_socket import GRPCSocket, GRPCStream
from purerpc.utils import is_linux, get_linux_kernel_version, AClosing, \
    print_memory_growth_statistics

from .grpclib.connection import GRPCConfiguration, GRPCConnection
from .grpclib.events import MessageReceived, RequestReceived, RequestEnded
from async_generator import async_generator, yield_


Stream = typing.AsyncIterator


class SerializingCallbackWrapper:
    def __init__(self, func, in_type, out_type):
        self.func = func
        self.in_type = in_type
        self.out_type = out_type

    @async_generator
    async def parsing_iterator(self, stream: GRPCStream):
        while True:
            event = await stream.recv()
            if isinstance(event, RequestEnded):
                return
            message = self.in_type()
            message.ParseFromString(event.data)
            await yield_(message)

    @async_generator
    async def __call__(self, stream: GRPCStream):
        input_message_stream = self.parsing_iterator(stream)
        async with AClosing(self.func(input_message_stream)) as temp:
            async for message in temp:
                await yield_(message.SerializeToString())


class Service:
    def __init__(self, name):
        self.name = name
        self.methods = {}

    def add_unary_unary(self, name, func, in_type, out_type):
        print("Call unary_unary")
        @async_generator
        async def wrapper(input_stream):
            message = None
            async for elem in input_stream:
                if message is not None:
                    # TODO: raise meaningful error
                    raise RuntimeError("Got multiple messages on unary stream")
                else:
                    message = elem
            result = await func(message)
            await yield_(result)
        self.add_stream_stream(name, wrapper, in_type, out_type)

    def add_unary_stream(self, name, func, in_type, out_type):
        print("Call unary_stream")
        @async_generator
        async def wrapper(input_stream):
            message = None
            async for elem in input_stream:
                if message is not None:
                    # TODO: raise meaningful error
                    raise RuntimeError("Got multiple messages on unary stream")
                else:
                    message = elem
            async for result in func(message):
                await yield_(result)
        self.add_stream_stream(name, wrapper, in_type, out_type)

    def add_stream_unary(self, name, func, in_type, out_type):
        print("Call stream_unary")
        @async_generator
        async def wrapper(input_stream):
            result = await func(input_stream)
            await yield_(result)
        self.add_stream_stream(name, wrapper, in_type, out_type)

    def add_stream_stream(self, name, func, in_type, out_type):
        print("Call stream_stream")
        self.methods[name] = SerializingCallbackWrapper(func, in_type, out_type)

    def rpc(self, method_name):
        def decorator(func):
            signature = inspect.signature(func)
            if signature.return_annotation == signature.empty:
                raise ValueError("Only annotated methods can be used with Service.rpc() decorator")
            if len(signature.parameters) != 1:
                raise ValueError("Only functions with one parameter can be used with Service.rpc("
                                 ") decorator")
            parameter = next(iter(signature.parameters.values()))
            if parameter.annotation == parameter.empty:
                raise ValueError("Only annotated methods can be used with Service.rpc() decorator")

            in_annotation = parameter.annotation
            out_annotation = signature.return_annotation

            if issubclass(in_annotation, Stream):
                in_type = in_annotation.__args__[0]
                in_stream = True
            else:
                in_type = in_annotation
                in_stream = False

            if issubclass(out_annotation, Stream):
                out_type = out_annotation.__args__[0]
                out_stream = True
            else:
                out_type = out_annotation
                out_stream = False

            param_tuple = (method_name, func, in_type, out_type)
            if in_stream and out_stream:
                self.add_stream_stream(*param_tuple)
            elif in_stream and not out_stream:
                self.add_stream_unary(*param_tuple)
            elif not in_stream and out_stream:
                self.add_unary_stream(*param_tuple)
            else:
                self.add_unary_unary(*param_tuple)

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

    async def _serve_async(self):
        # await curio.spawn(print_memory_growth_statistics(), daemon=True)
        await curio.tcp_server('', self.port, lambda c, a: ConnectionHandler(self)(c, a),
                               reuse_address=True, reuse_port=True)

    def _target_fn(self):
        curio.run(self._serve_async, with_monitor=True)

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

    async def request_received(self, stream: GRPCStream):
        await stream.start_response(stream.stream_id, "+proto")
        event = await stream.recv()

        try:
            service = self.server.services[event.service_name]
            method_fn = service.methods[event.method_name]
            async for message in method_fn(stream):
                await stream.send(message)
            await stream.close(0)
        except:
            logging.exception("Got exception while writing response stream")
            await stream.close(1, status_message=repr(sys.exc_info()))


    async def __call__(self, socket, addr):
        self.grpc_socket = GRPCSocket(self.config, socket)
        await self.grpc_socket.initiate_connection()

        # TODO: TaskGroup() uses a lot of memory if the connection is kept for a long time
        # TODO: do we really need it here?
        # task_group = curio.TaskGroup()
        try:
            async for stream in self.grpc_socket.listen():
                await curio.spawn(self.request_received(stream), daemon=True)
        except:
            logging.exception("Got exception in main dispatch loop")
        finally:
            # await task_group.join()
            await self.grpc_socket.shutdown()
