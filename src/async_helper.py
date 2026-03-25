"""Helper para rodar coroutines async em callbacks sync do Dash."""
import asyncio
import concurrent.futures

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def run_async(coro):
    """Roda uma coroutine async de forma sync."""
    return _executor.submit(asyncio.run, coro).result()
