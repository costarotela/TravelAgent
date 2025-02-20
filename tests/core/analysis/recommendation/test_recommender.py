"""Tests para el motor de recomendaciones."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Hotel,
    CustomerProfile,
    PackageVector,
    RecommendationScore,
    Recommendation,
)
from smart_travel_agency.core.analysis.recommendation import (
    get_recommendation_engine,
    RecommendationEngine,
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
    return TravelPackage(
        id="pkg1",
        hotel=sample_hotel,
        destination="Test City",
        check_in=datetime.now(),
        nights=5,
        total_price=1000.0,
        cancellation_policy="free",
        modification_policy="flexible",
        payment_options=["credit", "debit", "cash"],
    )


@pytest.fixture
def sample_packages(sample_hotel):
    """Lista de paquetes de prueba."""
    base_date = datetime.now()
    return [
        TravelPackage(
            id=f"pkg{i}",
            hotel=Hotel(
                id=f"hotel{i}",
                name=f"Test Hotel {i}",
                stars=3 + i % 3,
                review_score=7.5 + i % 3,
                amenities=["wifi", "pool"] if i < 2 else ["wifi", "pool", "spa", "gym"],
                popularity_index=0.6 + i * 0.1,
            ),
            destination="Test City",
            check_in=base_date + timedelta(days=i),
            nights=5,
            total_price=800.0 + i * 100,
            cancellation_policy="free" if i % 2 == 0 else "paid",
            modification_policy="flexible" if i % 2 == 0 else "strict",
            payment_options=(
                ["credit", "debit"] if i < 2 else ["credit", "debit", "cash"]
            ),
        )
        for i in range(10)
    ]


@pytest.fixture
def sample_profile():
    """Perfil de cliente de prueba."""
    return CustomerProfile(
        id="prof1",
        preferences={
            "price_range": (500, 2000),
            "min_stars": 3,
            "required_amenities": ["wifi", "pool"],
        },
        constraints={
            "max_budget": 2000,
            "date_range": (datetime.now(), datetime.now() + timedelta(days=30)),
        },
        interests=["beach", "spa", "nightlife"],
        history=[],
    )


@pytest.mark.asyncio
async def test_generate_recommendations(
    sample_profile, sample_package, sample_packages
):
    """Test de generación de recomendaciones."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Caso 1: Sin paquete actual
    recommendations = await engine.generate_recommendations(
        sample_profile, available_packages=sample_packages
    )

    # Verificar resultado
    assert isinstance(recommendations, list)
    assert len(recommendations) <= engine.config["max_recommendations"]

    for rec in recommendations:
        assert isinstance(rec, Recommendation)
        assert isinstance(rec.package, TravelPackage)
        assert isinstance(rec.score, RecommendationScore)
        assert rec.reason
        assert "timestamp" in rec.metadata

    # Caso 2: Con paquete actual
    recommendations = await engine.generate_recommendations(
        sample_profile,
        current_package=sample_package,
        available_packages=sample_packages,
    )

    # Verificar resultado
    assert isinstance(recommendations, list)
    assert len(recommendations) <= engine.config["max_recommendations"]

    # Verificar que el paquete actual no está en las recomendaciones
    assert all(r.package.id != sample_package.id for r in recommendations)


@pytest.mark.asyncio
async def test_update_profile(sample_profile, sample_package):
    """Test de actualización de perfil."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Caso 1: Ver paquete
    interaction = {"viewed_package": sample_package}

    updated = await engine.update_profile(sample_profile, interaction)

    assert isinstance(updated, CustomerProfile)
    assert updated.id == sample_profile.id

    # Caso 2: Actualizar restricciones
    interaction = {
        "budget_limit": 2500,
        "date_range": (datetime.now(), datetime.now() + timedelta(days=60)),
    }

    updated = await engine.update_profile(sample_profile, interaction)

    assert updated.constraints["max_budget"] == 2500
    assert updated.constraints["date_range"] == interaction["date_range"]

    # Caso 3: Agregar intereses
    interaction = {"interests": ["shopping", "culture"]}

    updated = await engine.update_profile(sample_profile, interaction)

    assert "shopping" in updated.interests
    assert "culture" in updated.interests


@pytest.mark.asyncio
async def test_vectorize_packages(sample_packages):
    """Test de vectorización de paquetes."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Vectorizar paquetes
    vectors = await engine._vectorize_packages(sample_packages)

    # Verificar resultado
    assert isinstance(vectors, dict)
    assert len(vectors) == len(sample_packages)

    for pkg_id, vector in vectors.items():
        assert isinstance(vector, PackageVector)
        assert 0 <= vector.price_score <= 1
        assert 0 <= vector.quality_score <= 1
        assert 0 <= vector.location_score <= 1
        assert 0 <= vector.amenities_score <= 1
        assert 0 <= vector.activities_score <= 1

    # Verificar cache
    assert all(pkg.id in engine.vector_cache for pkg in sample_packages)


@pytest.mark.asyncio
async def test_find_similar_packages(sample_package, sample_packages):
    """Test de búsqueda de paquetes similares."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Vectorizar paquetes
    vectors = await engine._vectorize_packages([sample_package] + sample_packages)

    # Buscar similares
    recommendations = await engine._find_similar_packages(
        sample_package, sample_packages, vectors
    )

    # Verificar resultado
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0
    assert all(r.package.id != sample_package.id for r in recommendations)

    # Verificar orden por similitud
    similarities = [r.metadata["similarity"] for r in recommendations]
    assert all(s1 >= s2 for s1, s2 in zip(similarities, similarities[1:]))


@pytest.mark.asyncio
async def test_rank_by_profile(sample_profile, sample_packages):
    """Test de ranking por perfil."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Vectorizar paquetes
    vectors = await engine._vectorize_packages(sample_packages)

    # Rankear paquetes
    recommendations = await engine._rank_by_profile(
        sample_profile, sample_packages, vectors
    )

    # Verificar resultado
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0

    # Verificar orden por score
    scores = [r.score.total_score for r in recommendations]
    assert all(s1 >= s2 for s1, s2 in zip(scores, scores[1:]))


@pytest.mark.asyncio
async def test_recommendation_score(sample_package):
    """Test de cálculo de score."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Vectorizar paquete
    vectors = await engine._vectorize_packages([sample_package])
    vector = vectors[sample_package.id]

    # Calcular score
    score = await engine._calculate_recommendation_score(
        sample_package, vector, 0.8  # base_score
    )

    # Verificar resultado
    assert isinstance(score, RecommendationScore)
    assert 0 <= score.total_score <= 1

    # Verificar componentes
    components = score.components
    assert "base_score" in components
    assert "price_score" in components
    assert "quality_score" in components
    assert "location_score" in components
    assert "amenities_score" in components
    assert "activities_score" in components
    assert "seasonality" in components


@pytest.mark.asyncio
async def test_error_handling():
    """Test de manejo de errores."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Caso: Sin paquetes disponibles
    with pytest.raises(ValueError):
        await engine.generate_recommendations(None, available_packages=[])

    # Caso: Perfil inválido
    with pytest.raises(ValueError):
        await engine.generate_recommendations(None, available_packages=[None])

    # Caso: Paquete inválido
    with pytest.raises(ValueError):
        await engine._vectorize_packages([None])


@pytest.mark.asyncio
async def test_cache_behavior(sample_package):
    """Test de comportamiento del caché."""
    # Obtener motor
    engine = await get_recommendation_engine()

    # Primera vectorización
    vectors1 = await engine._vectorize_packages([sample_package])
    vector1 = vectors1[sample_package.id]

    # Segunda vectorización (debería usar caché)
    vectors2 = await engine._vectorize_packages([sample_package])
    vector2 = vectors2[sample_package.id]

    # Verificar que son iguales
    assert vector1.price_score == vector2.price_score
    assert vector1.quality_score == vector2.quality_score
    assert vector1.location_score == vector2.location_score
    assert vector1.amenities_score == vector2.amenities_score
    assert vector1.activities_score == vector2.activities_score
