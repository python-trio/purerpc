import functools
import collections
import subprocess
import multiprocessing
import tempfile
import shutil
import os
import sys
import inspect
import importlib
import concurrent.futures
import contextlib
import time
import random
import string
from multiprocessing.connection import Connection

from tblib import pickling_support
pickling_support.install()

import forge
import anyio
from async_generator import aclosing

# work around pickle issue on macOS
if sys.platform == 'darwin':
    multiprocessing = multiprocessing.get_context('fork')


@contextlib.contextmanager
def compile_temp_proto(*relative_proto_paths):
    modules = []
    with tempfile.TemporaryDirectory() as temp_dir:
        sys.path.insert(0, temp_dir)
        try:
            for relative_proto_path in relative_proto_paths:
                proto_path = os.path.join(os.path.dirname(
                    inspect.currentframe().f_back.f_back.f_globals['__file__']),
                    relative_proto_path)
                proto_filename = os.path.basename(proto_path)
                proto_temp_path = os.path.join(temp_dir, proto_filename)
                shutil.copyfile(proto_path, proto_temp_path)
            for relative_proto_path in relative_proto_paths:
                proto_filename = os.path.basename(relative_proto_path)
                proto_temp_path = os.path.join(temp_dir, proto_filename)
                cmdline = [sys.executable, '-m', 'grpc_tools.protoc',
                           '--python_out=.', '--purerpc_out=.', '--grpc_python_out=.',
                           '-I' + temp_dir, proto_temp_path]
                subprocess.check_call(cmdline, cwd=temp_dir)

                pb2_module_name = proto_filename.replace(".proto", "_pb2")
                pb2_grpc_module_name = proto_filename.replace(".proto", "_pb2_grpc")
                grpc_module_name = proto_filename.replace(".proto", "_grpc")

                pb2_module = importlib.import_module(pb2_module_name)
                pb2_grpc_module = importlib.import_module(pb2_grpc_module_name)
                grpc_module = importlib.import_module(grpc_module_name)
                modules.extend((pb2_module, pb2_grpc_module, grpc_module))
            yield modules
        finally:
            sys.path.remove(temp_dir)


_WrappedResult = collections.namedtuple("_WrappedResult", ("result", "exc_info"))


def _wrap_gen_in_process(conn: Connection):
    def decorator(gen):
        @functools.wraps(gen)
        def new_func(*args, **kwargs):
            try:
                for elem in gen(*args, **kwargs):
                    conn.send(_WrappedResult(result=elem, exc_info=None))
            except:
                conn.send(_WrappedResult(result=None, exc_info=sys.exc_info()))
            finally:
                conn.close()
        return new_func
    return decorator


async def async_iterable_to_list(async_iterable):
    result = []
    async with aclosing(async_iterable) as async_iterable:
        async for value in async_iterable:
            result.append(value)
    return result


def random_payload(min_size=1000, max_size=100000):
    return "".join(random.choice(string.ascii_letters)
                   for _ in range(random.randint(min_size, max_size)))


@contextlib.contextmanager
def _run_context_manager_generator_in_process(cm_gen):
    parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
    target_fn = _wrap_gen_in_process(child_conn)(cm_gen)

    process = multiprocessing.Process(target=target_fn)
    process.start()
    try:
        wrapped_result = parent_conn.recv()
        if wrapped_result.exc_info is not None:
            raise wrapped_result.exc_info[0].with_traceback(*wrapped_result.exc_info[1:])
        else:
            yield wrapped_result.result
    finally:
        try:
            if parent_conn.poll():
                exc_info = parent_conn.recv().exc_info
                if exc_info is not None:
                    raise exc_info[0].with_traceback(*exc_info[1:])
        finally:
            process.terminate()
            process.join()
            parent_conn.close()


def _run_purerpc_service_in_process(service, ssl_context=None):
    # TODO: there is no reason to run the server as a separate process...
    #   just use serve_async().  This synchronous cm has timing problems,
    #   because the server may not be listening before yielding to the body.

    def target_fn():
        import purerpc
        import socket

        # Grab an ephemeral port in advance, because we need to yield the port
        # before blocking on serve()...
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]

        server = purerpc.Server(port=port, ssl_context=ssl_context)
        server.add_service(service)
        yield port
        server.serve()

        # async def sleep_10_seconds_then_die():
        #     await anyio.sleep(20)
        #     raise ValueError
        #
        # async def main():
        #     async with anyio.create_task_group() as tg:
        #         tg.start_soon(server.serve_async)
        #         tg.start_soon(sleep_10_seconds_then_die)
        #
        # import cProfile
        # cProfile.runctx("purerpc_run(main)", globals(), locals(), sort="tottime")

    return _run_context_manager_generator_in_process(target_fn)


@contextlib.contextmanager
def run_purerpc_service_in_process(service, ssl_context=None):
    with _run_purerpc_service_in_process(service, ssl_context=ssl_context) as port:
        # work around API issue, giving server a chance to listen
        time.sleep(.05)
        yield port


# TODO: remove grpcio dependency from tests.  There is no reason to unit test
#  grpc project's code, and it's blocking pypy support.
def run_grpc_service_in_process(add_handler_fn):
    def target_fn():
        import grpc
        server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=1))
        port = server.add_insecure_port('[::]:0')
        add_handler_fn(server)
        server.start()
        yield port
        while True:
            time.sleep(60)
    return _run_context_manager_generator_in_process(target_fn)


def run_tests_in_workers(*, target, num_workers):
    parent_conn, child_conn = multiprocessing.Pipe(duplex=False)

    @_wrap_gen_in_process(child_conn)
    def target_fn():
        target()
        yield

    processes = [multiprocessing.Process(target=target_fn) for _ in range(num_workers)]
    for process in processes:
        process.start()

    try:
        for _ in range(num_workers):
            wrapped_result = parent_conn.recv()
            if wrapped_result.exc_info is not None:
                raise wrapped_result.exc_info[0].with_traceback(*wrapped_result.exc_info[1:])
    finally:
        parent_conn.close()
        for process in processes:
            process.join()


def grpc_client_parallelize(num_workers):
    def decorator(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            def target():
                func(*args, **kwargs)
            run_tests_in_workers(target=target, num_workers=num_workers)

        new_func.__parallelized__ = True
        return new_func
    return decorator


def purerpc_client_parallelize(num_tasks):
    def decorator(corofunc):
        if not inspect.iscoroutinefunction(corofunc):
            raise TypeError("Expected coroutine function")

        @functools.wraps(corofunc)
        async def new_corofunc(**kwargs):
            async with anyio.create_task_group() as tg:
                for _ in range(num_tasks):
                    tg.start_soon(functools.partial(corofunc, **kwargs))
        return new_corofunc
    return decorator


def grpc_channel(port_fixture_name, channel_arg_name="channel"):
    def decorator(func):
        if hasattr(func, "__parallelized__") and func.__parallelized__:
            raise TypeError("Cannot pass gRPC channel to already parallelized test, grpc_client_parallelize should "
                            "be the last decorator in chain")

        @forge.compose(
            forge.copy(func),
            forge.modify(channel_arg_name, name=port_fixture_name, interface_name="port_fixture_value"),
        )
        def new_func(*, port_fixture_value, **kwargs):
            import grpc
            with grpc.insecure_channel('127.0.0.1:{}'.format(port_fixture_value)) as channel:
                func(**kwargs, channel=channel)

        return new_func
    return decorator


def purerpc_channel(port_fixture_name, channel_arg_name="channel"):
    def decorator(corofunc):
        if not inspect.iscoroutinefunction(corofunc):
            raise TypeError("Expected coroutine function")

        @forge.compose(
            forge.copy(corofunc),
            forge.modify(channel_arg_name, name=port_fixture_name, interface_name="port_fixture_value"),
        )
        async def new_corofunc(*, port_fixture_value, **kwargs):
            import purerpc
            async with purerpc.insecure_channel("127.0.0.1", port_fixture_value) as channel:
                await corofunc(**kwargs, channel=channel)

        return new_corofunc
    return decorator
