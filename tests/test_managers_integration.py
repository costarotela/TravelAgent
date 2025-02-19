"""
Pruebas de integración para los managers principales.
Verifica la interacción entre BudgetManager, ProviderIntegrationManager y BudgetReconstructionManager.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any
from unittest.mock import MagicMock, AsyncMock

from agent_core.schemas import (
    TravelPackage,
    CustomerProfile,
    SearchCriteria,
    Accommodation,
    Activity,
    Location,
    AccommodationType,
    PackageStatus,
    AnalysisResult,
)
from agent_core.managers.budget_manager import BudgetManager
from agent_core.managers.provider_integration_manager import ProviderIntegrationManager
from agent_core.managers.budget_reconstruction_manager import (
    BudgetReconstructionManager,
    ReconstructionStrategy,
)


class MockProvider:
    """Proveedor mock para pruebas."""

    def __init__(self):
        self.packages = {}
        self.search_results = []

    async def get_package_details(self, package_id: str) -> TravelPackage:
        return self.packages.get(package_id)

    async def search_packages(
        self, criteria: SearchCriteria, limit: int = None
    ) -> List[TravelPackage]:
        return self.search_results


@pytest.fixture
def mock_components():
    """Crear componentes mock básicos."""
    storage = AsyncMock()
    storage.get_timestamp = MagicMock(return_value=datetime.now().timestamp())

    events = AsyncMock()
    events.emit = AsyncMock()
    events.subscribe = MagicMock()
    events.unsubscribe = MagicMock()

    logger = MagicMock()
    metrics = MagicMock()
    cache = AsyncMock()

    return {
        "storage": storage,
        "events": events,
        "logger": logger,
        "metrics": metrics,
        "cache": cache,
    }


@pytest.fixture
def sample_package():
    """Crear paquete de ejemplo."""
    return TravelPackage(
        id="PKG-001",
        title="Aventura en la Patagonia",
        description="Experiencia única en el fin del mundo",
        destination="Patagonia, Argentina",
        price=Decimal("1500.00"),
        currency="USD",
        duration=7,
        start_date=datetime.now() + timedelta(days=30),
        end_date=datetime.now() + timedelta(days=37),
        provider="BestTravel",
        status=PackageStatus.AVAILABLE,
        accommodation=Accommodation(
            name="Hotel del Glaciar",
            type=AccommodationType.HOTEL,
            rating=4.5,
            stars=4,
            location=Location(
                country="Argentina", city="El Calafate", address="Av. del Glaciar 123"
            ),
        ),
    )


@pytest.fixture
def sample_customer():
    """Crear cliente de ejemplo."""
    return CustomerProfile(
        id="CUST-001", name="Juan Pérez", email="juan@example.com", segment="frequent"
    )


@pytest.fixture
def sample_criteria():
    """Crear criterios de búsqueda de ejemplo."""
    return SearchCriteria(
        destination="Patagonia",
        dates={
            "start": datetime.now().date() + timedelta(days=30),
            "end": datetime.now().date() + timedelta(days=37),
        },
        budget={"min": Decimal("1000.00"), "max": Decimal("2000.00")},
        travelers={"adults": 2, "children": 0},
    )


@pytest.fixture
async def integrated_managers(mock_components, sample_package):
    """Crear y configurar los tres managers integrados."""

    # Configurar mock provider
    provider = MockProvider()
    provider.packages["PKG-001"] = sample_package
    provider.search_results = [sample_package]

    # Crear managers
    budget_manager = BudgetManager(
        storage=mock_components["storage"],
        events=mock_components["events"],
        metrics=mock_components["metrics"],
        logger=mock_components["logger"],
    )

    provider_manager = ProviderIntegrationManager(
        storage=mock_components["storage"],
        cache=mock_components["cache"],
        logger=mock_components["logger"],
        metrics=mock_components["metrics"],
        events=mock_components["events"],
    )

    reconstruction_manager = BudgetReconstructionManager(
        storage=mock_components["storage"],
        logger=mock_components["logger"],
        metrics=mock_components["metrics"],
        events=mock_components["events"],
        budget_manager=budget_manager,
        provider_manager=provider_manager,
    )

    # Inicializar managers
    await budget_manager.initialize()
    await provider_manager.initialize()
    await reconstruction_manager.initialize()

    # Registrar provider
    await provider_manager.register_provider("BestTravel", provider)

    return {
        "budget_manager": budget_manager,
        "provider_manager": provider_manager,
        "reconstruction_manager": reconstruction_manager,
        "provider": provider,
    }


@pytest.mark.asyncio
async def test_budget_creation_and_update(
    integrated_managers, sample_package, sample_customer, sample_criteria
):
    """Probar creación de presupuesto y actualización por cambio de precios."""

    managers = integrated_managers

    # 1. Crear presupuesto inicial
    budget = await managers["budget_manager"].create_budget(
        sample_package, sample_criteria, sample_customer
    )

    assert budget["status"] == "active"
    assert budget["base_price"] == sample_package.price
    assert budget["package"]["id"] == sample_package.id

    # 2. Simular cambio de precio en proveedor
    updated_package = sample_package.model_copy(update={"price": Decimal("1600.00")})
    managers["provider"].packages["PKG-001"] = updated_package

    # 3. Detectar y procesar cambio
    changes = {
        "price": {
            "previous": float(sample_package.price),
            "current": float(updated_package.price),
            "difference": float(updated_package.price - sample_package.price),
            "percentage": 6.67,
        }
    }

    # 4. Analizar impacto
    impact = await managers["reconstruction_manager"].analyze_impact(
        budget["id"], changes
    )

    assert impact.impact_level > 0
    assert len(impact.changes) > 0

    # 5. Reconstruir presupuesto
    updated_budget = await managers["reconstruction_manager"].reconstruct_budget(
        budget["id"], changes
    )

    assert updated_budget["base_price"] == updated_package.price
    assert len(updated_budget["modifications"]) > 0


@pytest.mark.asyncio
async def test_alternative_package_suggestion(
    integrated_managers, sample_package, sample_customer, sample_criteria
):
    """Probar sugerencia de alternativas cuando hay cambios significativos."""

    managers = integrated_managers

    # 1. Crear presupuesto inicial
    budget = await managers["budget_manager"].create_budget(
        sample_package, sample_criteria, sample_customer
    )

    # 2. Simular cambio drástico en paquete original
    alternative_package = sample_package.model_copy(
        update={
            "price": Decimal("2500.00"),  # Aumento significativo
            "duration": 6,  # Cambio en duración
        }
    )
    managers["provider"].packages["PKG-001"] = alternative_package

    # 3. Detectar y procesar cambio
    changes = {
        "price": {
            "previous": float(sample_package.price),
            "current": float(alternative_package.price),
            "difference": float(alternative_package.price - sample_package.price),
            "percentage": 66.67,
        },
        "duration": {
            "previous": sample_package.duration,
            "current": alternative_package.duration,
            "difference": alternative_package.duration - sample_package.duration,
        },
    }

    # 4. Analizar impacto
    impact = await managers["reconstruction_manager"].analyze_impact(
        budget["id"], changes
    )

    assert impact.impact_level >= 0.7  # Impacto alto o muy alto
    assert len(impact.recommendations) > 0


@pytest.mark.asyncio
async def test_price_preservation_strategy(
    integrated_managers, sample_package, sample_customer, sample_criteria
):
    """Probar estrategia de preservación de precio ante cambios menores."""

    managers = integrated_managers

    # 1. Crear presupuesto inicial
    budget = await managers["budget_manager"].create_budget(
        sample_package, sample_criteria, sample_customer
    )

    original_final_price = budget["final_price"]

    # 2. Simular cambio menor en paquete
    updated_package = sample_package.model_copy(
        update={"price": Decimal("1550.00")}  # Aumento pequeño
    )
    managers["provider"].packages["PKG-001"] = updated_package

    # 3. Detectar y procesar cambio
    changes = {
        "price": {
            "previous": float(sample_package.price),
            "current": float(updated_package.price),
            "difference": float(updated_package.price - sample_package.price),
            "percentage": 3.33,
        }
    }

    # 4. Reconstruir presupuesto con estrategia de preservación
    updated_budget = await managers["reconstruction_manager"].reconstruct_budget(
        budget["id"], changes, strategy=ReconstructionStrategy.PRESERVE_PRICE
    )

    # El precio final debe mantenerse
    assert updated_budget["final_price"] == original_final_price
    assert "price_preserved" in updated_budget["metadata"]


@pytest.mark.asyncio
async def test_event_emission(integrated_managers, mock_components):
    """Probar emisión de eventos entre managers."""

    events = mock_components["events"]
    reconstruction_manager = integrated_managers["reconstruction_manager"]

    # Verificar suscripción a eventos
    events.subscribe.assert_any_call(
        "package_updated", reconstruction_manager._handle_package_update
    )
    events.subscribe.assert_any_call(
        "package_deleted", reconstruction_manager._handle_package_deletion
    )
    events.subscribe.assert_any_call(
        "budget_impact_high", reconstruction_manager._handle_high_impact
    )

    # Verificar emisión de eventos
    events.emit.assert_called
