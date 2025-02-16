"""Tests básicos del sistema."""

import pytest


def test_basic():
    """Test básico para verificar que pytest funciona."""
    assert True


@pytest.mark.asyncio
async def test_async():
    """Test básico para verificar que pytest-asyncio funciona."""
    assert True
