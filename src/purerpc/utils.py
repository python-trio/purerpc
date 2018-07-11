import platform
import curio
import pdb
import math


def is_linux():
    return platform.system() == "Linux"


def is_darwin():
    return platform.system() == "Darwin"


def get_linux_kernel_version():
    if not is_linux():
        return None
    release = platform.release()
    if not release:
        return None
    return tuple(map(int, release.split("-")[0].split(".")))


async def print_memory_growth_statistics(interval_sec=10.0, set_pdb_trace_every=math.inf):
    num_iters = 0
    import objgraph
    while True:
        num_iters += 1
        await curio.sleep(interval_sec)
        objgraph.show_growth()
        if num_iters == set_pdb_trace_every:
            pdb.set_trace()
            num_iters = 0
