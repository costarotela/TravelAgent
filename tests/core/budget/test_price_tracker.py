"""Tests for price tracker."""

import pytest
from datetime import datetime
from src.core.budget.price_tracker import PriceTracker
from src.core.models.travel import TravelPackage, PriceHistory


@pytest.mark.asyncio
async def test_track_price():
    """Test price tracking."""
    tracker = PriceTracker()
    package = TravelPackage(id="test-package", price=100.0, currency="USD")

    # Track price
    await tracker.track_price(package)

    # Verify price was tracked
    history = await tracker.get_price_history(package.id)
    assert history is not None
    assert history["current_price"] == 100.0
    assert history["currency"] == "USD"
    assert "last_updated" in history


@pytest.mark.asyncio
async def test_get_price_history():
    """Test getting price history."""
    tracker = PriceTracker()
    package_id = "test-package"

    # Test non-existent package
    history = await tracker.get_price_history(package_id)
    assert history is None

    # Add some history
    package = TravelPackage(id=package_id, price=100.0, currency="USD")
    await tracker.track_price(package)

    # Update price
    package.price = 110.0
    await tracker.track_price(package)

    # Get history
    history = await tracker.get_price_history(package_id)
    assert history is not None
    assert history["current_price"] == 110.0
    assert len(history["recent_prices"]) == 2
    assert history["recent_prices"][0]["price"] == 110.0
    assert history["recent_prices"][1]["price"] == 100.0
