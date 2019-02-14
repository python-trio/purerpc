import purerpc
import unittest.mock
import purerpc.server
from purerpc.test_utils import compile_temp_proto


def test_plugin(greeter_grpc):
    assert "GreeterServicer" in dir(greeter_grpc)
    assert "GreeterStub" in dir(greeter_grpc)

    GreeterServicer = greeter_grpc.GreeterServicer
    assert issubclass(GreeterServicer, purerpc.server.Servicer)
    assert "SayHello" in dir(GreeterServicer)
    assert callable(GreeterServicer.SayHello)
    assert "SayHelloToMany" in dir(GreeterServicer)

    assert callable(GreeterServicer.SayHelloToMany)
    assert "SayHelloGoodbye" in dir(GreeterServicer)
    assert callable(GreeterServicer.SayHelloGoodbye)
    assert "SayHelloToManyAtOnce" in dir(GreeterServicer)
    assert callable(GreeterServicer.SayHelloToManyAtOnce)
    assert isinstance(GreeterServicer().service, purerpc.Service)

    GreeterStub = greeter_grpc.GreeterStub
    channel = unittest.mock.MagicMock()
    greeter_stub = GreeterStub(channel)

    assert "SayHello" in dir(greeter_stub)
    assert callable(greeter_stub.SayHello)
    assert "SayHelloToMany" in dir(greeter_stub)
    assert callable(greeter_stub.SayHelloToMany)
    assert "SayHelloGoodbye" in dir(greeter_stub)
    assert callable(greeter_stub.SayHelloGoodbye)
    assert "SayHelloToManyAtOnce" in dir(greeter_stub)
    assert callable(greeter_stub.SayHelloToManyAtOnce)


def test_package_names_and_imports():
    with compile_temp_proto('data/test_package_names/A.proto',
                            'data/test_package_names/B.proto',
                            'data/test_package_names/C.proto'):
        # modules are imported by context manager
        # if there is no error then we are good.
        pass
