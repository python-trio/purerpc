import purerpc
import purerpc.server
from .test_case_base import PureRPCTestCase


class TestProtocPlugin(PureRPCTestCase):
    def test_plugin(self):
        with self.compile_temp_proto('data/greeter.proto') as (_, grpc_module):
            self.assertIn("GreeterServicer", dir(grpc_module))
            self.assertIn("GreeterStub", dir(grpc_module))

            GreeterServicer = grpc_module.GreeterServicer
            self.assertTrue(issubclass(GreeterServicer, purerpc.server.Servicer))
            self.assertIn("SayHello", dir(GreeterServicer))
            self.assertTrue(callable(GreeterServicer.SayHello))
            self.assertIn("SayHelloToMany", dir(GreeterServicer))
            self.assertTrue(callable(GreeterServicer.SayHelloToMany))
            self.assertIn("SayHelloGoodbye", dir(GreeterServicer))
            self.assertTrue(callable(GreeterServicer.SayHelloGoodbye))
            self.assertIn("SayHelloToManyAtOnce", dir(GreeterServicer))
            self.assertTrue(callable(GreeterServicer.SayHelloToManyAtOnce))
            self.assertTrue(isinstance(GreeterServicer().service, purerpc.Service))

            GreeterStub = grpc_module.GreeterStub
            channel = purerpc.Channel("localhost", 0)
            greeter_stub = GreeterStub(channel)
            self.assertIn("SayHello", dir(greeter_stub))
            self.assertTrue(callable(greeter_stub.SayHello))
            self.assertIn("SayHelloToMany", dir(greeter_stub))
            self.assertTrue(callable(greeter_stub.SayHelloToMany))
            self.assertIn("SayHelloGoodbye", dir(greeter_stub))
            self.assertTrue(callable(greeter_stub.SayHelloGoodbye))
            self.assertIn("SayHelloToManyAtOnce", dir(greeter_stub))
            self.assertTrue(callable(greeter_stub.SayHelloToManyAtOnce))

    def test_package_names_and_imports(self):
        with self.compile_temp_proto('data/test_package_names/A.proto',
                                     'data/test_package_names/B.proto',
                                     'data/test_package_names/C.proto'):
            # modules are imported by context manager
            # if there is no error then we are good.
            pass
