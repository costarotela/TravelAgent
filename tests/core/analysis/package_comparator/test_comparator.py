"""Tests para el comparador de paquetes."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Hotel,
    ComparisonResult,
    CompetitivePosition,
)
from smart_travel_agency.core.analysis.package_comparator import (
    get_package_comparator,
    PackageComparator,
    PackageFeatures,
    MarketAnalysis,
)


@pytest.fixture
def sample_hotel():
    """Hotel de prueba."""
    return Hotel(
        id="hotel1",
        name="Test Hotel",
        stars=4,
        review_score=8.5,
        amenities=["wifi", "pool", "spa"],
        popularity_index=0.8,
    )


@pytest.fixture
def sample_package(sample_hotel):
    """Paquete de prueba."""
    now = datetime.now()
    return TravelPackage(
        id="pkg1",
        hotel=sample_hotel,
        destination="Test City",
        start_date=now,
        end_date=now + timedelta(days=5),
        price=1000.0,
        currency="USD",
        provider="TestProvider",
        description="Test package",
        cancellation_policy="free",
        modification_policy="flexible",
        payment_options=["credit", "debit", "cash"],
    )


@pytest.fixture
def competitor_packages(sample_hotel):
    """Paquetes competidores."""
    base_date = datetime.now()
    return [
        TravelPackage(
            id=f"comp{i}",
            hotel=Hotel(
                id=f"hotel{i}",
                name=f"Comp Hotel {i}",
                stars=3 + i,
                review_score=7.5 + i,
                amenities=["wifi", "pool"] if i < 2 else ["wifi", "pool", "spa", "gym"],
                popularity_index=0.6 + i * 0.1,
            ),
            destination="Test City",
            start_date=base_date + timedelta(days=i),
            end_date=base_date + timedelta(days=i + 5),
            price=800.0 + i * 100,
            currency="USD",
            provider=f"CompProvider{i}",
            description=f"Competitor package {i}",
            cancellation_policy="free" if i % 2 == 0 else "paid",
            modification_policy="flexible" if i % 2 == 0 else "strict",
            payment_options=(
                ["credit", "debit"] if i < 2 else ["credit", "debit", "cash"]
            ),
        )
        for i in range(5)
    ]


@pytest.mark.asyncio
async def test_compare_packages(sample_package, competitor_packages):
    """Test de comparación de paquetes."""
    # Obtener comparador
    comparator = get_package_comparator()

    # Realizar comparación
    result = await comparator.compare_packages(sample_package, competitor_packages)

    # Verificar resultado
    assert isinstance(result, ComparisonResult)
    assert result.target_id == sample_package.id
    assert isinstance(result.position, CompetitivePosition)
    # Verificar que opportunities es una lista (puede estar vacía)
    assert isinstance(result.opportunities, list)

    # Verificar posición competitiva
    assert 0 <= result.position.price_percentile <= 1
    assert 0 <= result.position.quality_percentile <= 1
    assert 0 <= result.position.flexibility_percentile <= 1
    assert result.position.position in ["budget", "value", "premium"]


@pytest.mark.asyncio
async def test_analyze_market(competitor_packages):
    """Test de análisis de mercado."""
    # Obtener comparador
    comparator = get_package_comparator()

    # Realizar análisis
    result = await comparator.analyze_market(competitor_packages)

    # Verificar resultado
    assert isinstance(result, MarketAnalysis)
    assert hasattr(result, "price_analysis")
    assert hasattr(result, "quality_analysis")
    assert hasattr(result, "flexibility_analysis")
    assert hasattr(result, "seasonality_analysis")
    assert hasattr(result, "optimal_prices")
    assert hasattr(result, "metadata")


@pytest.mark.asyncio
async def test_extract_features(sample_package):
    """Test de extracción de características."""
    # Obtener comparador
    comparator = get_package_comparator()

    # Extraer características
    features = await comparator._extract_features(sample_package)

    # Verificar resultado
    assert isinstance(features, PackageFeatures)
    assert features.price_per_night > 0
    assert 0 <= features.quality_score <= 1
    assert 0 <= features.flexibility_score <= 1


@pytest.mark.asyncio
async def test_calculate_position(sample_package, competitor_packages):
    """Test de cálculo de posición competitiva."""
    # Obtener comparador
    comparator = get_package_comparator()

    # Extraer características
    target_features = await comparator._extract_features(sample_package)
    comp_features = [
        await comparator._extract_features(pkg) for pkg in competitor_packages
    ]

    # Calcular posición
    position = await comparator._calculate_position(target_features, comp_features)

    # Verificar resultado
    assert isinstance(position, CompetitivePosition)
    assert 0 <= position.price_percentile <= 1
    assert 0 <= position.quality_percentile <= 1
    assert 0 <= position.flexibility_percentile <= 1


@pytest.mark.asyncio
async def test_detect_opportunities(sample_package, competitor_packages):
    """Test de detección de oportunidades."""
    # Obtener comparador
    comparator = get_package_comparator()

    # Detectar oportunidades
    opportunities = await comparator.detect_opportunities(
        sample_package, competitor_packages
    )

    # Verificar resultado
    assert isinstance(opportunities, list)
    # Las oportunidades pueden estar vacías, pero si hay alguna, verificar su estructura
    for opp in opportunities:
        assert "type" in opp
        assert "description" in opp
        assert "impact" in opp


@pytest.mark.asyncio
async def test_error_handling():
    """Test de manejo de errores."""
    # Obtener comparador
    comparator = get_package_comparator()

    # Verificar error con datos insuficientes
    with pytest.raises(ValueError):
        await comparator.compare_packages(None, [])

    with pytest.raises(ValueError):
        await comparator.analyze_market([])


@pytest.mark.asyncio
async def test_cache_behavior(sample_package, competitor_packages):
    """Test de comportamiento del caché."""
    comparator = get_package_comparator()

    # Realizar dos comparaciones seguidas
    result1 = await comparator.compare_packages(sample_package, competitor_packages)
    result2 = await comparator.compare_packages(sample_package, competitor_packages)

    # Verificar que los resultados son consistentes (excluyendo timestamps)
    assert result1.target_id == result2.target_id
    assert result1.position.price_percentile == result2.position.price_percentile
    assert result1.position.quality_percentile == result2.position.quality_percentile
    assert (
        result1.position.flexibility_percentile
        == result2.position.flexibility_percentile
    )
    assert result1.position.position == result2.position.position
    assert result1.opportunities == result2.opportunities
    assert result1.metadata["num_competitors"] == result2.metadata["num_competitors"]
