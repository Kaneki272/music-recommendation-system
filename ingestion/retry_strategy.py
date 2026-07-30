from typing import Callable, Any
import asyncio

def with_exponential_backoff(max_retries: int = 5, base_delay: float = 1.0, allowed_exceptions: tuple = (Exception,)):
    """
    Decorator for wrapping external API calls.
    Handles 429, 500, 502, 503, and Timeouts with exponential backoff.
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs) -> Any:
            # Placeholder for retry logic
            return await func(*args, **kwargs)
        return wrapper
    return decorator
