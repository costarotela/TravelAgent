"""Data collection system for travel packages."""

from .models import PackageData, ProviderConfig, CollectionResult
from .providers import BaseProviderUpdater
from .collector import DataCollector
from .implementations.ola import OLAProviderUpdater
from .implementations.despegar import DespegarProviderUpdater

__all__ = [
    "PackageData",
    "ProviderConfig",
    "CollectionResult",
    "BaseProviderUpdater",
    "DataCollector",
    "OLAProviderUpdater",
    "DespegarProviderUpdater",
]
