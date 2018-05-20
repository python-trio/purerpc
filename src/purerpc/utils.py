import platform


def is_linux():
    return platform.system() == "Linux"


def get_linux_kernel_version():
    if not is_linux():
        return None
    release = platform.release()
    if not release:
        return None
    return tuple(map(int, release.split("-")[0].split(".")))


class AClosing:
    def __init__(self, async_gen):
        self._async_gen = async_gen

    async def __aenter__(self):
        return self._async_gen

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._async_gen.aclose()