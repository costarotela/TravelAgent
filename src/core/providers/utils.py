"""Utility functions and decorators for providers."""
import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)

logger = logging.getLogger(__name__)

# Tipos comunes de errores por proveedor
class ProviderError(Exception):
    """Base class for provider errors."""
    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")

class AuthenticationError(ProviderError):
    """Error during authentication."""
    pass

class RateLimitError(ProviderError):
    """Rate limit exceeded."""
    pass

class ConnectionError(ProviderError):
    """Connection error with provider."""
    pass

class ValidationError(ProviderError):
    """Invalid data or parameters."""
    pass

class AvailabilityError(ProviderError):
    """Resource not available."""
    pass

# Mapeo de códigos HTTP a excepciones específicas
ERROR_MAPPING = {
    401: AuthenticationError,
    403: AuthenticationError,
    429: RateLimitError,
    400: ValidationError,
    404: AvailabilityError
}

def map_http_error(status_code: int, provider: str, message: str) -> ProviderError:
    """Map HTTP status code to specific provider error."""
    error_class = ERROR_MAPPING.get(status_code, ProviderError)
    return error_class(message, provider)

def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    retry_exceptions: tuple = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
        RateLimitError
    )
):
    """Decorator for retrying provider operations with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            provider_name = args[0].__class__.__name__ if args else "Unknown"
            
            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=min_wait, max=max_wait),
                retry=retry_if_exception_type(retry_exceptions),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True
            )
            async def retry_operation():
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if isinstance(e, aiohttp.ClientResponseError):
                        raise map_http_error(
                            e.status,
                            provider_name,
                            str(e)
                        ) from e
                    elif isinstance(e, retry_exceptions):
                        raise
                    else:
                        raise ProviderError(
                            str(e),
                            provider_name,
                            original_error=e
                        ) from e

            try:
                return await retry_operation()
            except RetryError as e:
                logger.error(
                    f"Operation failed after {max_attempts} attempts in {provider_name}",
                    exc_info=e
                )
                raise ProviderError(
                    f"Operation failed after {max_attempts} attempts",
                    provider_name,
                    original_error=e
                ) from e

        return wrapper
    return decorator

class RateLimiter:
    """Rate limiter for provider API calls."""

    def __init__(
        self,
        calls: int,
        period: float,
        burst: Optional[int] = None
    ):
        """Initialize rate limiter.
        
        Args:
            calls: Number of calls allowed
            period: Time period in seconds
            burst: Optional burst size (allows temporary exceeding of rate)
        """
        self.calls = calls
        self.period = period
        self.burst = burst or calls
        self._tokens = self.burst
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Acquire a token for an API call."""
        async with self._lock:
            now = time.monotonic()
            # Replenish tokens based on time passed
            elapsed = now - self._last_update
            self._tokens = min(
                self.burst,
                self._tokens + elapsed * (self.calls / self.period)
            )
            self._last_update = now

            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        if not await self.acquire():
            raise RateLimitError(
                "Rate limit exceeded",
                "RateLimiter"
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
