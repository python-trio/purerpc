import asyncio
import h2.config
import h2.connection

class Connection:
    def __init__(self, host: str, port: int, loop: asyncio.AbstractEventLoop = None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._host = host
        self._port = port
        self._loop = loop
        config = h2.config.H2Configuration(client_side=True, header_encoding="utf-8")
        self._connection = h2.connection.H2Connection(config=config)

    async def handle(self):
        reader, writer = await asyncio.open_connection(host=self._host, port=self._port,
                                                       loop=self._loop)
        self._connection.initiate_connection()
        writer.write(self._connection.data_to_send())
        try:
            pass
        finally:
            writer.write(self._connection.data_to_send())
            await writer.drain()
            writer.close()



class Stub:
    def __init__(self, service_name: str):
        self._service_name = service_name
        self._methods = {}

    def rpc(self, method_name, request_type, response_type):
        pass

    def bind(self):
        pass