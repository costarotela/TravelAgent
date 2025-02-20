"""
Gestión de presupuestos y reconstrucción de precios.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import asyncio
import json

from ..interfaces import (
    StorageManager,
    EventEmitter,
    MetricsCollector,
    Logger,
    AgentComponent,
)
from ..schemas import TravelPackage, SearchCriteria, CustomerProfile, AnalysisResult


class BudgetManager(AgentComponent):
    """
    Gestiona la creación y actualización de presupuestos.

    Attributes:
        storage: Gestor de almacenamiento
        events: Emisor de eventos
        metrics: Colector de métricas
        logger: Logger del sistema
    """

    def __init__(
        self,
        storage: StorageManager,
        events: EventEmitter,
        metrics: MetricsCollector,
        logger: Logger,
    ):
        """Inicializar gestor de presupuestos."""
        super().__init__(logger, metrics, events)
        self.storage = storage
        self._active_budgets: Dict[str, Dict[str, Any]] = {}
        self.initialized = False

    async def initialize(self) -> None:
        """Inicializar el componente."""
        if self.initialized:
            return

        self.logger.info("Inicializando BudgetManager")
        # Suscribirse a eventos relevantes
        self.events.subscribe("package_updated", self.handle_package_update)
        self.events.subscribe("package_deleted", self.handle_package_deletion)

        # Inicializar caché y estructuras de datos
        await self.storage.init_collection("budgets")
        await self.storage.init_collection("budget_history")

        # Cargar presupuestos activos
        active_budgets = await self.storage.find("budgets", {"status": "active"})
        self._active_budgets = {b["id"]: b for b in active_budgets}

        self.initialized = True
        self.logger.info("BudgetManager inicializado")

    async def shutdown(self) -> None:
        """Cerrar el componente."""
        if not self.initialized:
            return

        self.logger.info("Cerrando BudgetManager")
        # Limpiar suscripciones a eventos
        self.events.unsubscribe("package_updated", self.handle_package_update)
        self.events.unsubscribe("package_deleted", self.handle_package_deletion)

        # Guardar estado actual
        for budget in self._active_budgets.values():
            await self.storage.update("budgets", budget["id"], budget)

        # Limpiar caché y recursos
        self._active_budgets.clear()

        self.initialized = False
        self.logger.info("BudgetManager cerrado")

    async def create_budget(
        self,
        package: TravelPackage,
        criteria: SearchCriteria,
        customer: CustomerProfile,
    ) -> Dict[str, Any]:
        """
        Crear un nuevo presupuesto basado en un paquete.

        Args:
            package: Paquete turístico base
            criteria: Criterios de búsqueda
            customer: Perfil del cliente

        Returns:
            Presupuesto creado con detalles
        """
        if not self.initialized:
            raise RuntimeError("BudgetManager no inicializado")

        self.logger.info(f"Creando presupuesto para paquete {package.id}")

        # Generar ID único
        budget_id = (
            f"BUD-{datetime.now().strftime('%Y%m%d')}-{len(self._active_budgets) + 1}"
        )

        # Calcular precio base
        base_price = self._calculate_base_price(package, criteria, customer)

        # Aplicar ajustes por perfil
        adjusted_price = self._apply_profile_adjustments(base_price, customer)

        # Crear presupuesto
        budget = {
            "id": budget_id,
            "package": package.dict(),
            "customer": customer.dict(),
            "criteria": criteria.dict(),
            "original_price": package.price,
            "base_price": base_price,
            "final_price": adjusted_price,
            "margin": (adjusted_price / base_price) - 1,  # Calcular margen
            "currency": package.currency,
            "status": "active",
            "created_at": self.storage.get_timestamp(),
            "valid_until": self.storage.get_timestamp() + 7 * 24 * 60 * 60,  # 7 días
            "modifications": [],
            "metadata": {},  # Inicializar metadata
        }

        # Guardar en memoria y persistencia
        self._active_budgets[budget_id] = budget
        await self.storage.create("budgets", budget)

        # Emitir evento
        await self.events.emit(
            "budget_created",
            {
                "budget_id": budget_id,
                "package_id": package.id,
                "customer_id": customer.id,
            },
        )

        # Registrar métrica
        self.metrics.increment("budgets_created")

        return budget

    async def update_budget(
        self, budget_id: str, changes: Dict[str, Any], reason: str = "manual_update"
    ) -> Dict[str, Any]:
        """
        Actualizar un presupuesto existente.

        Args:
            budget_id: ID del presupuesto
            changes: Cambios a aplicar
            reason: Razón de la actualización

        Returns:
            Presupuesto actualizado
        """
        if not self.initialized:
            raise RuntimeError("BudgetManager no inicializado")

        if budget_id not in self._active_budgets:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        self.logger.info(f"Actualizando presupuesto {budget_id}")

        # Obtener presupuesto actual
        budget = self._active_budgets[budget_id]

        # Validar cambios
        if not self._validate_changes(budget, changes):
            raise ValueError("Cambios inválidos")

        # Crear entrada de historial
        history_entry = {
            "timestamp": self.storage.get_timestamp(),
            "changes": changes,
            "reason": reason,
            "previous_state": budget.copy(),
        }

        # Aplicar cambios
        updated_budget = self._apply_changes(budget, changes)
        updated_budget["modifications"].append(history_entry)

        # Actualizar en memoria y persistencia
        self._active_budgets[budget_id] = updated_budget
        await self.storage.update("budgets", budget_id, updated_budget)

        # Guardar historial
        await self.storage.create(
            "budget_history", {"budget_id": budget_id, **history_entry}
        )

        # Emitir evento
        await self.events.emit(
            "budget_updated",
            {"budget_id": budget_id, "changes": changes, "reason": reason},
        )

        # Registrar métrica
        self.metrics.increment("budgets_updated")

        return updated_budget

    async def handle_package_update(self, event: Dict[str, Any]) -> None:
        """
        Manejar actualización de paquete.

        Args:
            event: Evento con detalles de la actualización
        """
        if not self.initialized:
            return

        package_id = event["package_id"]
        changes = event["changes"]

        self.logger.info(f"Manejando actualización de paquete {package_id}")

        # Buscar presupuestos afectados
        affected_budgets = [
            budget
            for budget in self._active_budgets.values()
            if budget["package"]["id"] == package_id and budget["status"] == "active"
        ]

        for budget in affected_budgets:
            try:
                # Analizar impacto
                analysis = self._analyze_impact(budget, changes)

                if analysis.impact_level > 0.7:  # Impacto alto
                    # Notificar y sugerir alternativas
                    await self.events.emit(
                        "budget_impact_high",
                        {"budget_id": budget["id"], "analysis": analysis.dict()},
                    )

                elif analysis.impact_level > 0.3:  # Impacto medio
                    # Reconstruir presupuesto
                    await self.update_budget(
                        budget["id"],
                        {
                            "price_adjustment": self._calculate_adjustment(
                                budget, changes
                            )
                        },
                        "package_update",
                    )

                else:  # Impacto bajo
                    # Actualizar sin cambios mayores
                    await self.update_budget(
                        budget["id"],
                        {"last_package_update": self.storage.get_timestamp()},
                        "package_update",
                    )

            except Exception as e:
                self.logger.error(
                    f"Error procesando presupuesto {budget['id']}: {str(e)}"
                )
                continue

    async def handle_package_deletion(self, event: Dict[str, Any]) -> None:
        """
        Manejar eliminación de paquete.

        Args:
            event: Evento con detalles de la eliminación
        """
        if not self.initialized:
            return

        package_id = event["package_id"]

        self.logger.info(f"Manejando eliminación de paquete {package_id}")

        # Buscar presupuestos afectados
        affected_budgets = [
            budget
            for budget in self._active_budgets.values()
            if budget["package"]["id"] == package_id and budget["status"] == "active"
        ]

        for budget in affected_budgets:
            # Marcar como inválido
            await self.update_budget(
                budget["id"],
                {"status": "invalid", "invalidation_reason": "package_deleted"},
                "package_deleted",
            )

            # Notificar
            await self.events.emit(
                "budget_invalidated",
                {"budget_id": budget["id"], "reason": "package_deleted"},
            )

    async def recalculate_budget(
        self, budget_id: str, new_package_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recalcular presupuesto con nuevos datos de paquete.

        Args:
            budget_id: ID del presupuesto
            new_package_data: Nuevos datos del paquete

        Returns:
            Presupuesto recalculado
        """
        if not self.initialized:
            raise RuntimeError("BudgetManager no inicializado")

        if budget_id not in self._active_budgets:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        budget = self._active_budgets[budget_id]

        # Recrear objetos para cálculo
        package = TravelPackage(**new_package_data)
        criteria = SearchCriteria(**budget["criteria"])
        customer = CustomerProfile(**budget["customer"])

        # Recalcular precios
        base_price = self._calculate_base_price(package, criteria, customer)
        adjusted_price = self._apply_profile_adjustments(base_price, customer)

        # Actualizar presupuesto
        changes = {
            "package": package.dict(),
            "base_price": base_price,
            "final_price": adjusted_price,
            "recalculated_at": self.storage.get_timestamp(),
        }

        return await self.update_budget(budget_id, changes, "recalculation")

    async def get_budget_history(self, budget_id: str) -> List[Dict[str, Any]]:
        """
        Obtener historial de modificaciones de un presupuesto.

        Args:
            budget_id: ID del presupuesto

        Returns:
            Lista de modificaciones ordenada por fecha
        """
        if not self.initialized:
            raise RuntimeError("BudgetManager no inicializado")

        if budget_id not in self._active_budgets:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        budget = self._active_budgets[budget_id]
        return budget["modifications"]

    def _calculate_base_price(
        self,
        package: TravelPackage,
        criteria: SearchCriteria,
        customer: CustomerProfile,
    ) -> Decimal:
        """Calcular precio base según criterios y perfil."""
        # Implementar lógica de cálculo
        return package.price

    def _apply_profile_adjustments(
        self, base_price: Decimal, customer: CustomerProfile
    ) -> Decimal:
        """Aplicar ajustes según perfil del cliente."""
        # Implementar lógica de ajustes
        return base_price

    def _validate_changes(
        self, budget: Dict[str, Any], changes: Dict[str, Any]
    ) -> bool:
        """Validar que los cambios sean aplicables."""
        # Implementar validación
        return True

    def _apply_changes(
        self, budget: Dict[str, Any], changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aplicar cambios al presupuesto."""
        # Implementar aplicación de cambios
        updated = budget.copy()
        updated.update(changes)
        return updated

    def _analyze_impact(
        self, budget: Dict[str, Any], changes: Dict[str, Any]
    ) -> AnalysisResult:
        """Analizar impacto de cambios en presupuesto."""
        # Implementar análisis
        return AnalysisResult(
            package_id=budget["package"]["id"],
            impact_level=0.5,
            changes=[changes],
            recommendations=[],
        )

    def _calculate_adjustment(
        self, budget: Dict[str, Any], changes: Dict[str, Any]
    ) -> Decimal:
        """Calcular ajuste de precio necesario."""
        # Implementar cálculo
        return Decimal("0.00")
