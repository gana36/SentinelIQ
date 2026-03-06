import asyncio
import functools
from typing import Callable, Type


def async_retry(max_attempts: int = 3, delay: float = 1.0, exceptions: tuple[Type[Exception], ...] = (Exception,)):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (2 ** attempt))
            raise last_exc
        return wrapper
    return decorator
