import os
import anyio
import logging

from anyio import run as _anyio_run

log = logging.getLogger(__name__)


def _new_run(func, *args, backend=None, backend_options=None):
    if backend is None:
        backend = os.getenv("PURERPC_BACKEND", "asyncio")
    log.info("Selected {} backend".format(backend))
    if backend == "uvloop":
        import uvloop
        uvloop.install()
        backend = "asyncio"
    return _anyio_run(func, *args, backend=backend, backend_options=backend_options)


def apply_monkeypatch():
    """Apply AnyIO monkeypatches (should merge upstream)"""
    anyio.run = _new_run
