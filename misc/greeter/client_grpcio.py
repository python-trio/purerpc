import grpc
from generated.greeter_pb2 import HelloRequest
from generated.greeter_pb2_grpc import GreeterStub


def main():
    channel = grpc.insecure_channel("localhost:50055")
    stub = GreeterStub(channel)
    data = "World" * 20000
    response = stub.SayHello(HelloRequest(name=data))
    assert(response.message == "Hello, " + data)

if __name__ == "__main__":
    main()
