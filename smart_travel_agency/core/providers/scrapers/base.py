"""Base classes for web scrapers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from ...schemas import Flight, Accommodation, Activity
from .config import ScraperConfig

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class AuthenticationError(ScraperError):
    """Raised when authentication fails."""
    pass


class BaseScraper(ABC):
    """Base class for web scrapers."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        config: Optional[ScraperConfig] = None
    ):
        """Initialize scraper.
        
        Args:
            base_url: Base URL for the provider
            username: Username for authentication
            password: Password for authentication
            config: Optional scraper configuration
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.config = config or ScraperConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agent = UserAgent()
        self._auth_token: Optional[str] = None
        self._last_auth: Optional[datetime] = None
        self._request_times: List[float] = []

    async def __aenter__(self):
        """Create session when entering context."""
        if not self.session:
            # Configure timeout
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            
            # Configure proxy if enabled
            if self.config.use_proxy and self.config.proxy_url:
                proxy = self.config.proxy_url
            else:
                proxy = None
            
            self.session = aiohttp.ClientSession(timeout=timeout, proxy=proxy)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session when exiting context."""
        if self.session:
            await self.session.close()
            self.session = None

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the provider."""
        pass

    @abstractmethod
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: datetime,
        return_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Flight]:
        """Search for flights."""
        pass

    @abstractmethod
    async def search_accommodations(
        self,
        destination: str,
        check_in: datetime,
        check_out: datetime,
        **kwargs
    ) -> List[Accommodation]:
        """Search for accommodations."""
        pass

    @abstractmethod
    async def search_activities(
        self,
        destination: str,
        date: datetime,
        **kwargs
    ) -> List[Activity]:
        """Search for activities."""
        pass

    async def _make_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth_required: bool = True,
        retry_count: int = 0
    ) -> BeautifulSoup:
        """Make an HTTP request and return parsed response.
        
        Args:
            method: HTTP method
            url: URL to request
            params: Query parameters
            data: Request body
            headers: Request headers
            auth_required: Whether authentication is required
            retry_count: Current retry attempt
            
        Returns:
            Parsed BeautifulSoup object
        """
        if not self.session:
            raise ScraperError("Session not initialized. Use context manager.")

        # Check rate limiting
        await self._check_rate_limit()

        if auth_required and not self._auth_token:
            await self.authenticate()

        # Build headers
        request_headers = {
            "User-Agent": self.user_agent.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": f"{self.config.language};q=0.9,en;q=0.8",
        }
        if headers:
            request_headers.update(headers)
        if self._auth_token:
            request_headers["Authorization"] = f"Bearer {self._auth_token}"
        if self.config.custom_headers:
            request_headers.update(self.config.custom_headers)

        # Make request
        try:
            async with self.session.request(
                method,
                urljoin(self.base_url, url),
                params=params,
                data=data,
                headers=request_headers,
                ssl=False  # For development only
            ) as response:
                # Record request time for rate limiting
                self._request_times.append(asyncio.get_event_loop().time())
                
                if response.status == 401:
                    raise AuthenticationError("Authentication failed")
                    
                if response.status == 429:  # Too Many Requests
                    if retry_count < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_delay)
                        return await self._make_request(
                            method, url,
                            params=params,
                            data=data,
                            headers=headers,
                            auth_required=auth_required,
                            retry_count=retry_count + 1
                        )
                    raise ScraperError("Rate limit exceeded")
                    
                response.raise_for_status()
                html = await response.text()
                
                # Save raw response if debug mode enabled
                if self.config.debug_mode and self.config.save_raw_responses:
                    self._save_raw_response(html, url)
                
                return BeautifulSoup(html, "html.parser")

        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {str(e)}")
            if retry_count < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay)
                return await self._make_request(
                    method, url,
                    params=params,
                    data=data,
                    headers=headers,
                    auth_required=auth_required,
                    retry_count=retry_count + 1
                )
            raise ScraperError(f"Request failed after {retry_count} retries: {str(e)}")

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        current_time = asyncio.get_event_loop().time()
        
        # Remove old requests from tracking
        self._request_times = [
            t for t in self._request_times
            if current_time - t <= 60  # Keep last minute
        ]
        
        # Check if we're over the limit
        if len(self._request_times) >= self.config.requests_per_minute:
            # Calculate wait time
            wait_time = 60 - (current_time - self._request_times[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)

    async def _extract_price(self, element: BeautifulSoup, selector: str) -> float:
        """Extract and normalize price from element.
        
        Args:
            element: BeautifulSoup element
            selector: CSS selector for price element
            
        Returns:
            Normalized price as float
        """
        try:
            price_element = element.select_one(selector)
            if not price_element:
                return 0.0
            
            # Remove currency symbol and normalize
            price_text = price_element.text.strip()
            price_text = "".join(c for c in price_text if c.isdigit() or c == ".")
            return float(price_text)

        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to extract price: {str(e)}")
            return 0.0

    def _save_raw_response(self, html: str, url: str) -> None:
        """Save raw response for debugging."""
        if self.config.debug_mode and self.config.save_raw_responses:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_response_{timestamp}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"<!-- URL: {url} -->\n")
                f.write(html)
