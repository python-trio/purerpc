import os

import purerpc
import purerpc.server
from .test_case_base import PureRPCTestCase


class TestClientServerSimple(PureRPCTestCase):
    def test_plugin(self):
        with self.compile_temp_proto('data/greeter.proto') as (_, grpc_module):
            self.assertIn("GreeterServicer", dir(grpc_module))
            self.assertIn("GreeterStub", dir(grpc_module))

            GreeterServicer = getattr(grpc_module, "GreeterServicer")
            self.assertTrue(issubclass(GreeterServicer, purerpc.server.Servicer))
            self.assertIn("SayHello", dir(GreeterServicer))
            self.assertTrue(callable(getattr(GreeterServicer, "SayHello")))
            self.assertIn("SayHelloToMany", dir(GreeterServicer))
            self.assertTrue(callable(getattr(GreeterServicer, "SayHelloToMany")))
            self.assertIn("SayHelloGoodbye", dir(GreeterServicer))
            self.assertTrue(callable(getattr(GreeterServicer, "SayHelloGoodbye")))
            self.assertIn("SayHelloToManyAtOnce", dir(GreeterServicer))
            self.assertTrue(callable(getattr(GreeterServicer, "SayHelloToManyAtOnce")))
            self.assertTrue(isinstance(GreeterServicer().service, purerpc.Service))

            GreeterStub = getattr(grpc_module, "GreeterStub")
            channel = purerpc.Channel("localhost", 0)
            greeter_stub = GreeterStub(channel)
            self.assertIn("SayHello", dir(greeter_stub))
            self.assertTrue(callable(getattr(greeter_stub, "SayHello")))
            self.assertIn("SayHelloToMany", dir(greeter_stub))
            self.assertTrue(callable(getattr(greeter_stub, "SayHelloToMany")))
            self.assertIn("SayHelloGoodbye", dir(greeter_stub))
            self.assertTrue(callable(getattr(greeter_stub, "SayHelloGoodbye")))
            self.assertIn("SayHelloToManyAtOnce", dir(greeter_stub))
            self.assertTrue(callable(getattr(greeter_stub, "SayHelloToManyAtOnce")))
