import os
import ssl
import anyio
import logging

from anyio import run as _anyio_run

log = logging.getLogger(__name__)

WantRead = (BlockingIOError, InterruptedError, ssl.SSLWantReadError)
WantWrite = (BlockingIOError, InterruptedError, ssl.SSLWantWriteError)


def _new_run(func, *args, backend=None, backend_options=None):
    if backend is None:
        backend = os.getenv("PURERPC_BACKEND", "asyncio")
    log.info("Selected {} backend".format(backend))
    _anyio_run(func, *args, backend=backend, backend_options=backend_options)


async def _new_sendall(self, data, *, flags=0):
    with memoryview(data).cast('B') as buffer:
        total_sent = 0
        while buffer:
            await self._check_cancelled()
            try:
                num_sent = self._raw_socket.send(buffer, flags)
                total_sent += num_sent
                buffer = buffer[num_sent:]
            except WantWrite:
                await self._wait_writable()
            except WantRead:  # pragma: no cover
                await self._wait_readable()
            except ssl.SSLEOFError:
                self._raw_socket.close()
                raise


def apply_monkeypatch():
    """Apply AnyIO monkeypatches (should merge upstream)"""
    anyio.run = _new_run
    anyio._networking.BaseSocket.sendall = _new_sendall