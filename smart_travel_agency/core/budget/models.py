"""
Módulo de modelos para el sistema de presupuestos.

Este módulo implementa:
1. Modelo de presupuesto y sus componentes
2. Versionado de presupuestos
3. Reconstrucción de presupuestos
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from ..schemas import TravelPackage
from .manager import get_budget_manager
from .reconstruction import get_reconstruction_manager, ReconstructionStrategy


@dataclass
class BudgetVersion:
    """Versión de un presupuesto."""

    version_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    changes: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario.

        Returns:
            Diccionario con los datos de la versión
        """
        return {
            "version_id": str(self.version_id),
            "timestamp": self.timestamp.isoformat(),
            "changes": self.changes,
            "reason": self.reason,
            "user_id": self.user_id,
            "metadata": self.metadata,
        }


@dataclass
class BudgetItem:
    """Item de presupuesto."""

    description: str
    amount: Decimal
    quantity: int = 1
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)
    item_id: UUID = field(default_factory=uuid4)
    version_id: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario.

        Returns:
            Diccionario con los datos del item
        """
        return {
            "description": self.description,
            "amount": float(self.amount),
            "quantity": self.quantity,
            "currency": self.currency,
            "metadata": self.metadata,
            "item_id": str(self.item_id),
            "version_id": str(self.version_id) if self.version_id else None,
        }

    @property
    def total_amount(self) -> Decimal:
        """Calcula el monto total del item."""
        return self.amount * self.quantity


@dataclass
class Budget:
    """Modelo de presupuesto."""

    items: List[BudgetItem]
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)
    budget_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    versions: List[BudgetVersion] = field(default_factory=list)
    current_version: Optional[UUID] = None

    def __post_init__(self):
        """Inicializar presupuesto."""
        # Si no hay versión inicial, crearla
        if not self.versions:
            version = BudgetVersion(
                changes={
                    "type": "creation",
                    "source": "direct",
                },
                reason="Creación directa de presupuesto",
                metadata={"items": [item.to_dict() for item in self.items]},
            )
            self.versions.append(version)
            self.current_version = version.version_id

            # Asignar version_id a los items
            for item in self.items:
                item.version_id = version.version_id

        # Registrar en el gestor de presupuestos
        manager = get_budget_manager()
        manager.register_budget(self)

    @property
    def total_amount(self) -> Decimal:
        """Calcula el monto total del presupuesto."""
        return sum(item.total_amount for item in self.items)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el presupuesto a diccionario."""
        return {
            "budget_id": str(self.budget_id),
            "currency": self.currency,
            "items": [item.to_dict() for item in self.items],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "total_amount": float(self.total_amount),
            "versions": [version.to_dict() for version in self.versions],
            "current_version": str(self.current_version) if self.current_version else None,
        }

    async def apply_changes(
        self,
        changes: Dict[str, Any],
        reason: str,
        user_id: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> None:
        """Aplicar cambios al presupuesto.

        Args:
            changes: Cambios a aplicar
            reason: Razón del cambio
            user_id: ID del usuario que realiza el cambio
            strategy: Estrategia de reconstrucción
        """
        # Analizar impacto de los cambios
        manager = get_reconstruction_manager()
        impact = await manager.analyze_impact(str(self.budget_id), changes)

        # Reconstruir presupuesto según estrategia
        if strategy:
            reconstructed = await manager.reconstruct_budget(
                str(self.budget_id), changes, strategy
            )
            self.items = reconstructed.items
            self.metadata.update(reconstructed.metadata)

        # Registrar nueva versión
        version = BudgetVersion(
            changes=changes,
            reason=reason,
            user_id=user_id,
            metadata={
                "impact": impact.to_dict(),
                "strategy": strategy,
            },
        )
        self.versions.append(version)
        self.current_version = version.version_id

        # Actualizar items con nueva versión
        for item in self.items:
            item.version_id = version.version_id

        # Actualizar última modificación
        self.last_modified = datetime.now()

    async def get_reconstruction_suggestions(
        self, changes: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Obtener sugerencias de reconstrucción.

        Args:
            changes: Cambios propuestos

        Returns:
            Lista de sugerencias
        """
        manager = get_reconstruction_manager()
        impact = await manager.analyze_impact(str(self.budget_id), changes)

        suggestions = []

        # Sugerir preservar margen si el impacto es alto
        if impact.impact_level > 0.1:  # 10% o más
            suggestions.append({
                "strategy": "preserve_margin",
                "description": "Preservar el margen ajustando los precios proporcionalmente",
                "impact_level": impact.impact_level,
                "price_impact": impact.price_impact,
                "estimated_impact": {
                    "margin_change": 0,
                    "price_change": impact.price_impact,
                },
            })

        # Sugerir preservar precios si el impacto es moderado
        if 0.05 <= impact.impact_level <= 0.2:  # Entre 5% y 20%
            suggestions.append({
                "strategy": "preserve_price",
                "description": "Mantener los precios actuales ajustando el margen",
                "impact_level": impact.impact_level,
                "price_impact": impact.price_impact,
                "estimated_impact": {
                    "margin_change": impact.impact_level,
                    "price_change": 0,
                },
            })

        # Sugerir ajuste proporcional si el impacto es bajo
        if impact.impact_level < 0.1:  # Menos del 10%
            suggestions.append({
                "strategy": "adjust_proportionally",
                "description": "Distribuir el impacto proporcionalmente entre precios y margen",
                "impact_level": impact.impact_level,
                "price_impact": impact.price_impact,
                "estimated_impact": {
                    "margin_change": impact.impact_level / 2,
                    "price_change": impact.price_impact / 2,
                },
            })

        return suggestions


def create_budget_from_package(package: TravelPackage) -> Budget:
    """Crear un presupuesto a partir de un paquete de viaje."""
    # Crear items del presupuesto
    items = []

    # Vuelos
    for flight in package.flights:
        items.append(
            BudgetItem(
                description=f"Vuelo: {flight.origin} -> {flight.destination}",
                amount=Decimal(flight.price),
                quantity=1,
                currency=flight.currency,
                metadata={
                    "type": "flight",
                    "flight_data": flight.to_dict(),
                    "provider": flight.provider,
                },
            )
        )

    # Alojamiento
    for accommodation in package.accommodations:
        items.append(
            BudgetItem(
                description=f"Alojamiento: {accommodation.name}",
                amount=Decimal(accommodation.price_per_night),
                quantity=accommodation.nights,
                currency=accommodation.currency,
                metadata={
                    "type": "accommodation",
                    "accommodation_data": accommodation.to_dict(),
                    "provider": accommodation.provider,
                },
            )
        )

    # Actividades
    for activity in package.activities:
        items.append(
            BudgetItem(
                description=f"Actividad: {activity.name}",
                amount=Decimal(activity.price),
                quantity=1,
                currency=activity.currency,
                metadata={
                    "type": "activity",
                    "activity_data": activity.to_dict(),
                    "provider": activity.provider,
                },
            )
        )

    # Seguro
    if package.insurance:
        items.append(
            BudgetItem(
                description=f"Seguro: {package.insurance.coverage_type}",
                amount=Decimal(package.insurance.price),
                quantity=1,
                currency=package.insurance.currency,
                metadata={
                    "type": "insurance",
                    "insurance_data": package.insurance.to_dict(),
                    "provider": package.insurance.provider,
                },
            )
        )

    # Crear presupuesto
    budget = Budget(items=items)

    # Actualizar metadata de la versión inicial con datos del paquete
    version = budget.versions[0]  # Ya existe una versión inicial creada en __post_init__
    version.changes.update({
        "type": "creation",
        "package_id": str(package.package_id),
        "source": "package_conversion",
    })
    version.reason = "Creación desde paquete de viaje"
    version.metadata["package_data"] = package.to_dict()

    return budget
