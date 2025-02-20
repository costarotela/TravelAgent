"""Configuration for scrapers."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ScraperConfig:
    """Base configuration for scrapers."""
    
    # Timeouts y reintentos
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    
    # Rate limiting
    requests_per_minute: int = 60
    concurrent_requests: int = 10
    
    # Cache
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hora
    
    # Proxy configuration
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    
    # Headers personalizados
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Filtros de búsqueda
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    excluded_airlines: List[str] = field(default_factory=list)
    preferred_airlines: List[str] = field(default_factory=list)
    min_rating: float = 0.0
    
    # Preferencias de extracción
    extract_reviews: bool = False
    extract_images: bool = False
    extract_detailed_itinerary: bool = False
    extract_cancellation_policy: bool = True
    extract_baggage_info: bool = True
    
    # Moneda y localización
    preferred_currency: str = "USD"
    language: str = "es"
    
    # Flags para desarrollo
    debug_mode: bool = False
    save_raw_responses: bool = False


@dataclass
class OlaScraperConfig(ScraperConfig):
    """Specific configuration for Ola.com scraper."""
    
    base_url: str = "https://www.ola.com"
    api_version: str = "v2"
    
    # Preferencias específicas de Ola
    include_promo_codes: bool = True
    include_nearby_airports: bool = True
    flexible_dates: bool = False
    flexible_dates_range: int = 3


@dataclass
class AeroScraperConfig(ScraperConfig):
    """Specific configuration for Aero.com.ar scraper."""
    
    base_url: str = "https://www.aero.com.ar"
    api_version: str = "v1"
    
    # Preferencias específicas de Aero
    include_stop_sales: bool = False
    include_charter_flights: bool = False
    show_prices_with_tax: bool = True


# Configuraciones por defecto
DEFAULT_OLA_CONFIG = OlaScraperConfig(
    requests_per_minute=30,  # Más conservador con Ola
    preferred_currency="USD",
    language="es",
    extract_cancellation_policy=True,
    extract_baggage_info=True
)

DEFAULT_AERO_CONFIG = AeroScraperConfig(
    requests_per_minute=40,
    preferred_currency="ARS",
    language="es",
    extract_cancellation_policy=True,
    extract_baggage_info=True
)
