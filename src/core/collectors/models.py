"""Models for data collection system."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PackageData(BaseModel):
    """Normalized package data from any provider."""

    provider: str
    destination: str
    price: float
    currency: str = "USD"
    dates: List[datetime]
    availability: int
    package_id: str
    details: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ProviderConfig(BaseModel):
    """Configuration for a provider."""

    name: str
    base_url: str
    rate_limit_interval: int = 2
    max_retries: int = 3
    timeout: int = 30
    proxy: Optional[str] = None
    headers: dict = Field(default_factory=dict)
    cache_ttl: int = 300  # 5 minutes
    metadata: dict = Field(default_factory=dict)


class CollectionResult(BaseModel):
    """Result of a data collection operation."""

    success: bool
    provider: str
    destination: str
    packages: List[PackageData] = Field(default_factory=list)
    error: Optional[str] = None
    duration_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
