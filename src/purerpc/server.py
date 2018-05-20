import collections
import sys
import inspect
import warnings
from multiprocessing import Process

import curio
import typing
import logging

from purerpc.utils import is_linux, get_linux_kernel_version, AClosing

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
    async def parsing_iterator(self, input_stream: curio.Queue):
        async for data in input_stream:
            if data is None:
                return
            message = self.in_type()
            message.ParseFromString(data)
            await yield_(message)

    @async_generator
    async def __call__(self, input_queue: curio.Queue):
        input_message_stream = self.parsing_iterator(input_queue)
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
        await curio.tcp_server('', self.port, lambda c, a: ConnectionHandler(self)(c, a),
                               reuse_address=True, reuse_port=True)

    def _target_fn(self):
        curio.run(self._serve_async)

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

        config = GRPCConfiguration(client_side=False)
        self.connection = GRPCConnection(config=config)
        self.server = server

        self.request_message_queue = {}

        self.write_event = curio.Event()
        self.write_shutdown = False
        self.stream = None

    async def stream_writer(self):
        # TODO: this should be the single thread that writes to self.stream, communication with
        # this thread should go through special event self.write_event
        # The logic is simple:
        # while True:
        #   while self.connection.data_to_send() > 0:
        #      await self.stream.sendall(...)
        #   await self.write_event.wait()
        # TODO: second option: use StrictFIFOLock and write data in the threads that generate it
        while True:
            await self.write_event.wait()
            self.write_event.clear()
            while True:
                data = self.connection.data_to_send()
                if not data:
                    break
                await self.stream.sendall(data)
            if self.write_shutdown:
                return

    async def ping_writer(self):
        await self.write_event.set()

    async def request_received(self, event: RequestReceived):
        self.connection.start_response(event.stream_id, "+proto")
        await self.ping_writer()

        try:
            service = self.server.services[event.service_name]
            method_fn = service.methods[event.method_name]
            async for message in method_fn(self.request_message_queue[event.stream_id]):
                self.connection.send_message(event.stream_id, message)
                await self.ping_writer()

            self.connection.end_response(event.stream_id, 0)
            await self.ping_writer()
        except:
            logging.exception("Got exception while writing response stream")
            self.connection.end_response(event.stream_id, 1, status_message=repr(sys.exc_info()))
            await self.ping_writer()
        finally:
            del self.request_message_queue[event.stream_id]

    async def message_received(self, event: MessageReceived):
        await self.request_message_queue[event.stream_id].put(event.data)

    async def request_ended(self, event: RequestEnded):
        await self.request_message_queue[event.stream_id].put(None)

    async def __call__(self, client, addr):
        self.stream = client
        await curio.spawn(self.stream_writer(), daemon=True)
        self.connection.initiate_connection()
        await self.ping_writer()

        task_group = curio.TaskGroup()
        try:
            while True:
                data = await client.recv(self.RECEIVE_BUFFER_SIZE)
                if not data:
                    return
                events = self.connection.receive_data(data)
                for event in events:
                    if isinstance(event, RequestReceived):
                        # start RPC thread
                        self.request_message_queue[event.stream_id] = curio.Queue(10)
                        await task_group.spawn(self.request_received, event)
                    elif isinstance(event, RequestEnded):
                        await self.request_ended(event)
                    elif isinstance(event, MessageReceived):
                        await self.message_received(event)
                await self.ping_writer()
        except:
            logging.exception("Got exception in main dispatch loop")
        finally:
            await task_group.join()
            self.write_shutdown = True
            await self.ping_writer()
