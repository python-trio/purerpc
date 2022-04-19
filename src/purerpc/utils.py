import logging
import os
import platform

import anyio

_log = logging.getLogger(__name__)


def is_linux():
    return platform.system() == "Linux"


def is_darwin():
    return platform.system() == "Darwin"


def is_windows():
    return platform.system() == "Windows"


def run(func, *args, backend=None, backend_options=None):
    """wrapper for anyio.run() with some purerpc-specific conventions

      * if `backend` is None, read it from PURERPC_BACKEND environment variable,
        (still defaulting to asyncio)
      * allow "uvloop" as a value of `backend` (normally uvloop needs to
        be specified via `backend_options` under asyncio)
      * if uvloop is selected, raise ModuleNotFoundError if uvloop isn't installed
    """

    if backend is None:
        backend = os.getenv("PURERPC_BACKEND", "asyncio")
    _log.info("purerpc.run() selected {} backend".format(backend))
    if backend == "uvloop":
        backend = "asyncio"
        options = dict(use_uvloop=True)
        if backend_options is None:
            backend_options = options
        else:
            backend_options.update(options)
    if backend == "asyncio" and backend_options and backend_options.get('use_uvloop'):
        # Since anyio.run() will silently fall back when uvloop isn't available,
        # make the requirement explicit.
        import uvloop
    return anyio.run(func, *args, backend=backend, backend_options=backend_options)
