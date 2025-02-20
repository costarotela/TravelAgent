"""Tests para el sistema de reconstrucción de presupuestos."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import asyncio

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Flight,
    Accommodation,
    Activity,
    Insurance,
)
from smart_travel_agency.core.budget.models import (
    Budget,
    BudgetItem,
    BudgetVersion,
    create_budget_from_package,
)
from smart_travel_agency.core.budget.reconstruction import (
    ReconstructionStrategy,
    get_reconstruction_manager,
    initialize_reconstruction_manager,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def initialized_reconstruction_manager(event_loop):
    """Initialize the reconstruction manager."""
    await initialize_reconstruction_manager()
    manager = get_reconstruction_manager()
    yield manager
    # Cleanup
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


@pytest.fixture
def sample_package():
    """Fixture que crea un paquete de viaje de ejemplo."""
    now = datetime.now()
    start_date = now + timedelta(days=30)
    end_date = start_date + timedelta(days=7)

    return TravelPackage(
        package_id=UUID("12345678-1234-5678-1234-567812345678"),
        provider="test_provider",
        currency="USD",
        flights=[
            Flight(
                flight_id=UUID("11111111-1234-5678-1234-567812345678"),
                provider="test_airline",
                origin="GRU",
                destination="EZE",
                departure_time=start_date,
                arrival_time=start_date + timedelta(hours=2),
                flight_number="TEST123",
                airline="Test Air",
                price=Decimal("500.00"),
                currency="USD",
                passengers=2,
            )
        ],
        accommodations=[
            Accommodation(
                accommodation_id=UUID("22222222-1234-5678-1234-567812345678"),
                provider="test_hotel",
                hotel_id="TEST_HOTEL",
                name="Test Hotel",
                room_type="Standard",
                price_per_night=Decimal("200.00"),
                currency="USD",
                nights=7,
                check_in=start_date,
                check_out=end_date,
            )
        ],
        activities=[
            Activity(
                activity_id=UUID("33333333-1234-5678-1234-567812345678"),
                provider="test_activity",
                name="City Tour",
                description="Tour por la ciudad",
                price=Decimal("100.00"),
                currency="USD",
                duration=timedelta(hours=4),
                date=start_date + timedelta(days=1),
                participants=2,
            )
        ],
        insurance=Insurance(
            insurance_id=UUID("44444444-1234-5678-1234-567812345678"),
            provider="test_insurance",
            coverage_type="Full Coverage",
            price=Decimal("150.00"),
            currency="USD",
        ),
    )


@pytest.mark.asyncio
async def test_budget_creation_with_version(sample_package, initialized_reconstruction_manager):
    """Test que verifica la creación de presupuesto con versión inicial."""
    budget = create_budget_from_package(sample_package)

    # Verificar que se creó la versión inicial
    assert len(budget.versions) == 1
    assert budget.current_version is not None
    
    # Verificar que los items tienen el version_id correcto
    for item in budget.items:
        assert item.version_id == budget.current_version

    # Verificar metadata de la versión inicial
    version = budget.versions[0]
    assert version.changes["type"] == "creation"
    assert version.changes["package_id"] == str(sample_package.package_id)
    assert version.reason == "Creación desde paquete de viaje"
    assert "package_data" in version.metadata


@pytest.mark.asyncio
async def test_budget_apply_changes(initialized_reconstruction_manager):
    """Test que verifica la aplicación de cambios al presupuesto."""
    # Crear presupuesto simple
    items = [
        BudgetItem(
            description="Test Item",
            amount=Decimal("100.00"),
            quantity=1,
        )
    ]
    budget = Budget(items=items)

    # Aplicar cambios
    changes = {
        "price_adjustment": 0.1,  # 10% de incremento
        "reason": "Ajuste por temporada alta",
    }
    
    await budget.apply_changes(
        changes=changes,
        reason="Ajuste de precios por temporada",
        user_id="test_user",
    )

    # Verificar que se creó una nueva versión
    assert len(budget.versions) == 2  # Versión inicial + nueva versión
    assert budget.current_version == budget.versions[-1].version_id

    # Verificar que los cambios se registraron correctamente
    latest_version = budget.versions[-1]
    assert latest_version.changes == changes
    assert latest_version.reason == "Ajuste de precios por temporada"
    assert latest_version.user_id == "test_user"


@pytest.mark.asyncio
async def test_reconstruction_strategies(initialized_reconstruction_manager):
    """Test que verifica las diferentes estrategias de reconstrucción."""
    # Crear presupuesto simple
    items = [
        BudgetItem(
            description="Hotel",
            amount=Decimal("100.00"),
            quantity=3,
        ),
        BudgetItem(
            description="Vuelo",
            amount=Decimal("500.00"),
            quantity=1,
        ),
    ]
    budget = Budget(items=items)

    # Probar cada estrategia
    strategies = [
        ReconstructionStrategy.PRESERVE_MARGIN,
        ReconstructionStrategy.PRESERVE_PRICE,
        ReconstructionStrategy.ADJUST_PROPORTIONALLY,
        ReconstructionStrategy.BEST_ALTERNATIVE,
    ]

    changes = {
        "price_increase": {
            "hotel": 0.15,  # 15% incremento en hotel
            "flight": 0.05,  # 5% incremento en vuelo
        }
    }

    for strategy in strategies:
        # Aplicar cambios con diferentes estrategias
        await budget.apply_changes(
            changes=changes,
            reason=f"Test de estrategia {strategy}",
            strategy=strategy,
        )

        # Verificar que se creó una nueva versión
        latest_version = budget.versions[-1]
        assert latest_version.metadata["strategy"] == strategy


@pytest.mark.asyncio
async def test_get_reconstruction_suggestions(initialized_reconstruction_manager):
    """Test que verifica la obtención de sugerencias de reconstrucción."""
    # Crear presupuesto con múltiples items
    items = [
        BudgetItem(
            description="Hotel 5 estrellas",
            amount=Decimal("300.00"),
            quantity=5,
            metadata={"type": "accommodation", "stars": 5},
        ),
        BudgetItem(
            description="Vuelo directo",
            amount=Decimal("1000.00"),
            quantity=1,
            metadata={"type": "flight", "stops": 0},
        ),
    ]
    budget = Budget(items=items)

    # Solicitar sugerencias para cambios significativos
    changes = {
        "price_increase": {
            "accommodation": 0.50,  # 50% incremento en hotel
            "flight": 0.30,  # 30% incremento en vuelo
        }
    }

    suggestions = await budget.get_reconstruction_suggestions(changes)

    # Verificar que se obtuvieron sugerencias
    assert len(suggestions) > 0
    for suggestion in suggestions:
        assert "strategy" in suggestion
        assert "estimated_impact" in suggestion
        assert "description" in suggestion
