"""Scrapers package."""

from .base import BaseScraper, ScraperError, AuthenticationError
from .ola_scraper import OlaScraper
from .aero_scraper import AeroScraper

__all__ = [
    "BaseScraper",
    "ScraperError",
    "AuthenticationError",
    "OlaScraper",
    "AeroScraper"
]
