import anyio
import trio

async def main():
    async with anyio.open_cancel_scope():
        pass

trio.run(main)
