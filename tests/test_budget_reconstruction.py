"""Tests para el sistema de reconstrucción de presupuestos."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
import asyncio

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Flight,
    Accommodation,
    Activity,
    Insurance,
    Budget,
    BudgetItem,
)
from smart_travel_agency.core.budget.reconstruction import (
    ReconstructionStrategy,
    get_reconstruction_manager,
)
from smart_travel_agency.core.budget.reconstructor import get_budget_reconstructor
from smart_travel_agency.core.budget.manager import get_budget_manager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def reconstruction_system():
    """Get reconstruction system components."""
    reconstructor = await get_budget_reconstructor()  # Ya devuelve la instancia
    manager = await get_reconstruction_manager()  # Esperar la corutina
    budget_manager = get_budget_manager()  # No es una corutina
    yield reconstructor, manager, budget_manager
    # Cleanup
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


@pytest.fixture
async def sample_package():
    """Create a sample travel package for testing."""
    now = datetime.now()
    return TravelPackage(
        package_id=UUID("12345678-1234-5678-1234-567812345678"),
        provider="test_provider",
        currency="USD",
        flights=[
            Flight(
                flight_id=UUID("12345678-1234-5678-1234-567812345679"),
                provider="test_airline",
                origin="GRU",
                destination="EZE",
                departure_time=now,
                arrival_time=now + timedelta(hours=2),
                flight_number="TA123",
                airline="Test Airlines",
                price=Decimal("500.00"),
                currency="USD",
                passengers=1,
            )
        ],
        accommodations=[
            Accommodation(
                accommodation_id=UUID("12345678-1234-5678-1234-567812345680"),
                provider="test_hotel",
                hotel_id="TEST_HOTEL",
                name="Test Hotel",
                room_type="Standard",
                price_per_night=Decimal("100.00"),
                currency="USD",
                nights=7,
                check_in=now + timedelta(days=1),
                check_out=now + timedelta(days=8),
            )
        ],
        activities=[
            Activity(
                activity_id=UUID("12345678-1234-5678-1234-567812345681"),
                provider="test_activity",
                name="Test Activity",
                description="A test activity",
                price=Decimal("50.00"),
                currency="USD",
                duration=timedelta(hours=2),
                date=now + timedelta(days=2),
                participants=1,
            )
        ],
        insurance=Insurance(
            insurance_id=UUID("12345678-1234-5678-1234-567812345682"),
            provider="test_insurance",
            coverage_type="Basic",
            price=Decimal("100.00"),
            currency="USD",
        ),
    )


@pytest.mark.asyncio
async def test_budget_creation_with_version(sample_package, reconstruction_system):
    """Test que verifica la creación de presupuesto con versión inicial."""
    reconstructor, manager, budget_manager = reconstruction_system
    
    # Crear presupuesto inicial
    budget = Budget(
        id=str(uuid4()),
        items=[
            BudgetItem(
                id=str(item.flight_id),
                type="flight",
                category="transportation",
                price=item.price,
                cost=item.price * Decimal("0.9"),  # 10% margin
                rating=4.5,
                availability=1.0,
                dates={
                    "departure": item.departure_time,
                    "arrival": item.arrival_time
                },
                attributes={
                    "airline": item.airline,
                    "flight_number": item.flight_number,
                    "origin": item.origin,
                    "destination": item.destination
                }
            )
            for item in sample_package.flights
        ],
        criteria={
            "price_range": (Decimal("0"), Decimal("10000")),
            "dates": {
                "start": datetime.now(),
                "end": datetime.now() + timedelta(days=30)
            }
        },
        dates={
            "created": datetime.now(),
            "valid_until": datetime.now() + timedelta(days=7)
        },
        metadata={
            "source": "test",
            "version": 1
        }
    )
    
    # Registrar presupuesto
    await budget_manager.register_budget(budget)
    
    assert budget is not None
    assert len(budget.items) == 1  # Solo el vuelo por ahora
    total = sum(item.price for item in budget.items)
    assert total == Decimal("500.00")


@pytest.mark.asyncio
async def test_budget_apply_changes(reconstruction_system):
    """Test que verifica la aplicación de cambios al presupuesto."""
    reconstructor, manager, budget_manager = reconstruction_system
    
    # Crear presupuesto de prueba
    budget = Budget(
        id=str(uuid4()),
        items=[
            BudgetItem(
                id=str(uuid4()),
                type="flight",
                category="transportation",
                price=Decimal("500.00"),
                cost=Decimal("450.00"),
                rating=4.5,
                availability=1.0,
                dates={
                    "departure": datetime.now(),
                    "arrival": datetime.now() + timedelta(hours=2)
                },
                attributes={
                    "airline": "Test Airlines",
                    "flight_number": "TA123"
                }
            )
        ],
        criteria={},
        dates={
            "created": datetime.now()
        }
    )
    
    # Registrar presupuesto
    await budget_manager.register_budget(budget)
    
    # Aplicar cambios
    changes = {
        budget.items[0].id: {
            "price_change": 50.00,
        }
    }
    
    result = await manager.apply_reconstruction(
        budget_id=budget.id,
        changes=changes,
        strategy_name="preserve_margin"
    )
    
    assert result is not None
    assert result.success
    assert Decimal(str(result.changes_applied[budget.items[0].id]["new_price"])) == Decimal("550.00")  # 500.00 + 50.00
    assert Decimal(str(result.changes_applied[budget.items[0].id]["margin"])) == Decimal("50.00")  # Margen se mantiene igual


@pytest.mark.asyncio
async def test_reconstruction_strategies(reconstruction_system):
    """Test que verifica las diferentes estrategias de reconstrucción."""
    reconstructor, manager, budget_manager = reconstruction_system
    
    # Crear presupuesto de prueba
    budget = Budget(
        id=str(uuid4()),
        items=[
            BudgetItem(
                id=str(uuid4()),
                type="flight",
                category="transportation",
                price=Decimal("500.00"),
                cost=Decimal("450.00"),
                rating=4.5,
                availability=1.0,
                dates={
                    "departure": datetime.now(),
                    "arrival": datetime.now() + timedelta(hours=2)
                },
                attributes={
                    "airline": "Test Airlines",
                    "flight_number": "TA123"
                }
            )
        ],
        criteria={},
        dates={
            "created": datetime.now()
        }
    )
    
    # Registrar presupuesto
    await budget_manager.register_budget(budget)
    
    changes = {
        budget.items[0].id: {
            "price_change": 50.00,
        }
    }
    
    # Probar cada estrategia
    strategies = [
        "preserve_margin",
        "preserve_price",
        "adjust_proportional",
    ]
    
    for strategy in strategies:
        result = await manager.apply_reconstruction(
            budget_id=budget.id,
            changes=changes,
            strategy_name=strategy
        )
        assert result is not None
        assert result.success
        assert budget.items[0].id in result.changes_applied


@pytest.mark.asyncio
async def test_session_management(reconstruction_system):
    """Test que verifica el manejo de sesiones."""
    reconstructor, manager, budget_manager = reconstruction_system
    
    budget_id = str(uuid4())
    seller_id = "seller-123"
    
    # Iniciar sesión
    session = await manager.start_reconstruction_session(budget_id, seller_id)
    assert session is not None
    assert session.budget_id == budget_id
    assert session.seller_id == seller_id
    
    # Finalizar sesión
    await manager.end_reconstruction_session(budget_id, seller_id)
