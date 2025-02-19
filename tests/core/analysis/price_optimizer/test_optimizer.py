"""Tests para el optimizador de precios."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Hotel,
    OptimizationResult,
    PricingStrategy,
    DemandForecast
)
from smart_travel_agency.core.analysis.price_optimizer import (
    get_price_optimizer,
    PriceOptimizer,
    PriceFactors
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
        popularity_index=0.8
    )

@pytest.fixture
def sample_package(sample_hotel):
    """Paquete de prueba."""
    return TravelPackage(
        id="pkg1",
        hotel=sample_hotel,
        destination="Test City",
        check_in=datetime.now(),
        nights=5,
        total_price=1000.0,
        cancellation_policy="free",
        modification_policy="flexible",
        payment_options=["credit", "debit", "cash"]
    )

@pytest.fixture
def pricing_strategies():
    """Estrategias de pricing."""
    return [
        PricingStrategy(type="competitive"),
        PricingStrategy(type="value_based"),
        PricingStrategy(type="dynamic")
    ]

@pytest.mark.asyncio
async def test_optimize_price(
    sample_package,
    pricing_strategies
):
    """Test de optimización de precios."""
    # Obtener optimizador
    optimizer = await get_price_optimizer()
    
    for strategy in pricing_strategies:
        # Optimizar precio
        result = await optimizer.optimize_price(
            sample_package,
            strategy
        )
        
        # Verificar resultado
        assert isinstance(result, OptimizationResult)
        assert result.original_price == sample_package.total_price
        assert result.optimized_price > 0
        assert result.margin >= optimizer.config["min_margin"]
        assert result.margin <= optimizer.config["max_margin"]
        assert result.roi > 0
        
        # Verificar factores
        assert "base_cost" in result.factors
        assert "margin" in result.factors
        assert "seasonality" in result.factors
        assert "demand" in result.factors
        assert "competition" in result.factors
        assert "quality" in result.factors
        
        # Verificar metadata
        assert result.metadata["strategy"] == strategy.type
        assert "timestamp" in result.metadata
        assert "duration" in result.metadata

@pytest.mark.asyncio
async def test_forecast_demand():
    """Test de pronóstico de demanda."""
    # Obtener optimizador
    optimizer = await get_price_optimizer()
    
    # Parámetros
    destination = "Test City"
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    # Generar pronóstico
    result = await optimizer.forecast_demand(
        destination,
        start_date,
        end_date
    )
    
    # Verificar resultado
    assert isinstance(result, DemandForecast)
    assert result.destination == destination
    assert result.start_date == start_date
    assert result.end_date == end_date
    assert len(result.daily_demand) == 31  # 30 días + hoy
    assert 0 <= result.confidence <= 1
    
    # Verificar metadata
    assert "training_samples" in result.metadata
    assert "timestamp" in result.metadata

@pytest.mark.asyncio
async def test_seasonality_factor():
    """Test de factor de estacionalidad."""
    # Obtener optimizador
    optimizer = await get_price_optimizer()
    
    # Parámetros
    destination = "Test City"
    date = datetime.now()
    
    # Obtener factor
    factor = await optimizer.get_seasonality_factor(
        date,
        destination
    )
    
    # Verificar resultado
    assert isinstance(factor, float)
    assert factor > 0
    
    # Verificar cache
    cache_key = f"{destination}_{date.month}"
    assert destination in optimizer.seasonality_cache
    assert cache_key in optimizer.seasonality_cache[destination]
    
    # Segunda llamada (debería usar cache)
    factor2 = await optimizer.get_seasonality_factor(
        date,
        destination
    )
    
    assert factor == factor2

@pytest.mark.asyncio
async def test_extract_price_factors(
    sample_package
):
    """Test de extracción de factores."""
    # Obtener optimizador
    optimizer = await get_price_optimizer()
    
    # Extraer factores
    factors = await optimizer._extract_price_factors(sample_package)
    
    # Verificar resultado
    assert isinstance(factors, PriceFactors)
    assert factors.base_cost > 0
    assert 0 <= factors.margin <= 1
    assert factors.seasonality > 0
    assert 0 <= factors.demand <= 1
    assert 0 <= factors.competition <= 1
    assert 0 <= factors.quality <= 1

@pytest.mark.asyncio
async def test_pricing_strategies(
    sample_package
):
    """Test de estrategias de pricing."""
    # Obtener optimizador
    optimizer = await get_price_optimizer()
    
    # Extraer factores base
    factors = await optimizer._extract_price_factors(sample_package)
    base_price = factors.base_cost * (1 + factors.margin)
    
    # Test competitive pricing
    comp_price = await optimizer._competitive_pricing(
        sample_package,
        base_price,
        factors
    )
    assert isinstance(comp_price, float)
    assert comp_price > 0
    
    # Test value-based pricing
    value_price = await optimizer._value_based_pricing(
        sample_package,
        base_price,
        factors
    )
    assert isinstance(value_price, float)
    assert value_price > 0
    
    # Test dynamic pricing
    dynamic_price = await optimizer._dynamic_pricing(
        sample_package,
        base_price,
        factors
    )
    assert isinstance(dynamic_price, float)
    assert dynamic_price > 0

@pytest.mark.asyncio
async def test_error_handling():
    """Test de manejo de errores."""
    # Obtener optimizador
    optimizer = await get_price_optimizer()
    
    # Caso: Paquete inválido
    with pytest.raises(ValueError):
        await optimizer.optimize_price(
            None,
            PricingStrategy(type="competitive")
        )
    
    # Caso: Estrategia inválida
    with pytest.raises(ValueError):
        await optimizer.optimize_price(
            None,
            PricingStrategy(type="invalid")
        )
    
    # Caso: Pronóstico sin datos
    with pytest.raises(ValueError):
        await optimizer.forecast_demand(
            "",
            datetime.now(),
            datetime.now()
        )

@pytest.mark.asyncio
async def test_model_persistence():
    """Test de persistencia del modelo."""
    # Obtener optimizador
    optimizer = await get_price_optimizer()
    
    # Parámetros
    destination = "Test City"
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    # Primer pronóstico
    result1 = await optimizer.forecast_demand(
        destination,
        start_date,
        end_date
    )
    
    # Segundo pronóstico (mismo modelo)
    result2 = await optimizer.forecast_demand(
        destination,
        start_date,
        end_date
    )
    
    # Verificar consistencia
    assert result1.confidence == result2.confidence
    assert len(result1.daily_demand) == len(result2.daily_demand)
    
    for (date1, demand1), (date2, demand2) in zip(
        result1.daily_demand,
        result2.daily_demand
    ):
        assert date1 == date2
        assert demand1 == demand2
