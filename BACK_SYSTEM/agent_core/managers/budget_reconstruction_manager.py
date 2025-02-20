"""
Gestor de reconstrucción de presupuestos.
Maneja la actualización y reconstrucción inteligente de presupuestos.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import asyncio
from ..schemas import TravelPackage, CustomerProfile, SearchCriteria, AnalysisResult
from ..interfaces import (
    StorageManager,
    EventEmitter,
    MetricsCollector,
    Logger,
    AgentComponent,
)


class ReconstructionStrategy:
    """Define estrategias de reconstrucción de presupuestos."""

    PRESERVE_MARGIN = "preserve_margin"
    PRESERVE_PRICE = "preserve_price"
    ADJUST_PROPORTIONALLY = "adjust_proportionally"
    BEST_ALTERNATIVE = "best_alternative"


class BudgetReconstructionManager(AgentComponent):
    """
    Gestor de reconstrucción que maneja:
    1. Análisis de impacto de cambios
    2. Reconstrucción inteligente de presupuestos
    3. Notificación de cambios significativos
    4. Preservación de condiciones importantes
    """

    def __init__(
        self,
        storage: StorageManager,
        logger: Logger,
        metrics: MetricsCollector,
        events: EventEmitter,
        budget_manager: "BudgetManager",
        provider_manager: "ProviderIntegrationManager",
    ):
        super().__init__(logger, metrics, events)
        self.storage = storage
        self.budget_manager = budget_manager
        self.provider_manager = provider_manager
        self._reconstruction_tasks: Dict[str, asyncio.Task] = {}
        self.initialized = False

    async def initialize(self) -> None:
        """Inicializar el componente."""
        if self.initialized:
            return

        self.logger.info("Inicializando BudgetReconstructionManager")

        # Inicializar colecciones
        await self.storage.init_collection("reconstruction_history")
        await self.storage.init_collection("reconstruction_strategies")

        # Suscribirse a eventos relevantes
        self.events.subscribe("package_updated", self._handle_package_update)
        self.events.subscribe("package_deleted", self._handle_package_deletion)
        self.events.subscribe("budget_impact_high", self._handle_high_impact)

        # Cargar estrategias personalizadas
        strategies = await self.storage.find(
            "reconstruction_strategies", {"status": "active"}
        )
        for strategy in strategies:
            # Aquí podrías tener lógica para cargar estrategias personalizadas
            self.logger.info(f"Estrategia {strategy['id']} cargada")

        self.initialized = True
        self.logger.info("BudgetReconstructionManager inicializado")

    async def shutdown(self) -> None:
        """Cerrar el componente."""
        if not self.initialized:
            return

        self.logger.info("Cerrando BudgetReconstructionManager")

        # Cancelar todas las tareas de reconstrucción
        for task in self._reconstruction_tasks.values():
            task.cancel()

        # Esperar a que todas las tareas terminen
        if self._reconstruction_tasks:
            await asyncio.gather(
                *self._reconstruction_tasks.values(), return_exceptions=True
            )

        # Limpiar estado
        self._reconstruction_tasks.clear()

        # Desuscribirse de eventos
        self.events.unsubscribe("package_updated", self._handle_package_update)
        self.events.unsubscribe("package_deleted", self._handle_package_deletion)
        self.events.unsubscribe("budget_impact_high", self._handle_high_impact)

        self.initialized = False
        self.logger.info("BudgetReconstructionManager cerrado")

    async def analyze_impact(
        self, budget_id: str, changes: Dict[str, Any]
    ) -> AnalysisResult:
        """
        Analizar impacto de cambios en un presupuesto.
        """
        budget = self.budget_manager._active_budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        severity = self._calculate_severity(changes)
        affected_components = self._identify_affected_components(changes)
        price_impact = self._calculate_price_impact(budget["final_price"], changes)
        alternatives_needed = self._check_alternatives_needed(changes)
        recommended_strategy = self._determine_strategy(changes, budget)

        self.record_metric("budget_impacts.analyzed", 1, {"severity": severity})

        return AnalysisResult(
            budget_id=budget_id,
            package_id=budget["package"]["id"],
            impact_level=severity,
            changes=[changes],  # Convertir a lista de cambios
            price_impact=price_impact,
            recommendations=[recommended_strategy] if alternatives_needed else [],
        )

    async def reconstruct_budget(
        self, budget_id: str, changes: Dict[str, Any], strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reconstruir presupuesto basado en cambios detectados.
        """
        impact = await self.analyze_impact(budget_id, changes)

        if not strategy:
            strategy = (
                impact.recommendations[0]
                if impact.recommendations
                else ReconstructionStrategy.ADJUST_PROPORTIONALLY
            )

        reconstruction_method = self._get_reconstruction_method(strategy)

        updated_budget = await reconstruction_method(
            budget_id, changes, impact.model_dump()
        )

        await self.events.emit(
            "budget_reconstructed",
            {
                "budget_id": budget_id,
                "impact": impact.model_dump(),
                "strategy_used": strategy,
                "timestamp": datetime.now().isoformat(),
            },
        )

        return updated_budget

    async def suggest_alternatives(
        self, budget_id: str, changes: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Sugerir alternativas cuando la reconstrucción no es óptima.
        """
        budget = self.budget_manager._active_budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        original_package = TravelPackage(**budget["package"])
        criteria = SearchCriteria(**budget["criteria"])

        # Buscar alternativas similares
        provider_results = await self.provider_manager.search_packages(criteria)

        alternatives = []
        for provider_id, package in provider_results:
            if package.id != original_package.id:
                similarity = self._calculate_package_similarity(
                    original_package, package
                )
                if similarity >= 0.7:  # 70% similar o más
                    alternatives.append(
                        {
                            "package": package.model_dump(),
                            "provider_id": provider_id,
                            "similarity_score": similarity,
                            "price_difference": float(
                                package.price - original_package.price
                            ),
                        }
                    )

        # Ordenar por similitud y precio
        alternatives.sort(
            key=lambda x: (x["similarity_score"], -abs(x["price_difference"])),
            reverse=True,
        )

        return alternatives[:5]  # Retornar top 5 alternativas

    async def _handle_package_update(self, event_data: Dict[str, Any]) -> None:
        """
        Manejar eventos de actualización de paquetes.
        """
        package_id = event_data["package_id"]
        changes = event_data["changes"]

        # Buscar presupuestos afectados
        affected_budgets = [
            budget_id
            for budget_id, budget in self.budget_manager._active_budgets.items()
            if budget["package"]["id"] == package_id
        ]

        for budget_id in affected_budgets:
            if budget_id in self._reconstruction_tasks:
                continue

            self._reconstruction_tasks[budget_id] = asyncio.create_task(
                self._process_budget_update(budget_id, changes)
            )

    async def _handle_package_deletion(self, event_data: Dict[str, Any]) -> None:
        """
        Manejar eventos de eliminación de paquetes.
        """
        package_id = event_data["package_id"]

        # Buscar presupuestos afectados
        affected_budgets = [
            budget_id
            for budget_id, budget in self.budget_manager._active_budgets.items()
            if budget["package"]["id"] == package_id
        ]

        for budget_id in affected_budgets:
            if budget_id in self._reconstruction_tasks:
                continue

            # Crear cambios que reflejen la eliminación
            changes = {
                "status": {"previous": "available", "current": "deleted"},
                "availability": {"previous": 1, "current": 0},
            }

            self._reconstruction_tasks[budget_id] = asyncio.create_task(
                self._process_budget_update(budget_id, changes)
            )

    async def _handle_high_impact(self, event_data: Dict[str, Any]) -> None:
        """
        Manejar eventos de alto impacto en presupuestos.
        """
        budget_id = event_data["budget_id"]
        changes = event_data["changes"]

        if budget_id in self._reconstruction_tasks:
            return

        # Buscar alternativas automáticamente
        alternatives = await self.suggest_alternatives(budget_id, changes)

        if alternatives:
            await self.events.emit(
                "alternatives_found",
                {
                    "budget_id": budget_id,
                    "alternatives": alternatives,
                    "reason": "high_impact_changes",
                },
            )

        # Intentar reconstrucción con estrategia de preservación
        self._reconstruction_tasks[budget_id] = asyncio.create_task(
            self.reconstruct_budget(
                budget_id, changes, strategy=ReconstructionStrategy.PRESERVE_PRICE
            )
        )

    async def _process_budget_update(
        self, budget_id: str, changes: Dict[str, Any]
    ) -> None:
        """
        Procesar actualización de presupuesto.
        """
        try:
            impact = await self.analyze_impact(budget_id, changes)

            if impact.impact_level >= 0.7:  # Impacto alto
                # Emitir evento de alto impacto
                await self.events.emit(
                    "budget_impact_high",
                    {
                        "budget_id": budget_id,
                        "changes": changes,
                        "impact": impact.model_dump(),
                    },
                )

                # Si el impacto es muy alto, buscar alternativas
                if impact.impact_level >= 0.9:
                    alternatives = await self.suggest_alternatives(budget_id, changes)
                    if alternatives:
                        await self.events.emit(
                            "alternatives_found",
                            {
                                "budget_id": budget_id,
                                "alternatives": alternatives,
                                "reason": "high_impact_changes",
                            },
                        )

        except Exception as e:
            self.logger.error(f"Error processing budget update {budget_id}: {str(e)}")
        finally:
            if budget_id in self._reconstruction_tasks:
                del self._reconstruction_tasks[budget_id]

    def _calculate_severity(self, changes: Dict[str, Any]) -> float:
        """
        Calcular severidad de los cambios (0-1).
        """
        severity = 0.0
        weights = {
            "price": 0.6,  # El precio es el factor más importante
            "duration": 0.2,
            "dates": 0.1,
            "accommodation": 0.1,
        }

        if "price" in changes:
            price_change = changes["price"]
            percentage = abs(price_change.get("percentage", 0))
            # Cambios de precio > 10% son considerados de alto impacto
            severity += weights["price"] * min(percentage / 10, 1.0)

        if "duration" in changes:
            duration_change = changes["duration"]
            diff = abs(duration_change.get("difference", 0))
            # Cambios de duración de más de 2 días son de alto impacto
            severity += weights["duration"] * min(diff / 2, 1.0)

        if "dates" in changes:
            dates_change = changes["dates"]
            days_diff = abs(dates_change.get("difference_days", 0))
            # Cambios de fecha de más de 7 días son de alto impacto
            severity += weights["dates"] * min(days_diff / 7, 1.0)

        if "accommodation" in changes:
            # Cualquier cambio en alojamiento es considerado de impacto medio
            severity += weights["accommodation"]

        return severity

    def _identify_affected_components(self, changes: Dict[str, Any]) -> List[str]:
        """
        Identificar componentes afectados por cambios.
        """
        components = []

        if "price" in changes:
            components.append("price")
        if "availability" in changes:
            components.append("availability")
        if "status" in changes:
            components.append("status")

        return components

    def _calculate_price_impact(
        self, current_price: Decimal, changes: Dict[str, Any]
    ) -> float:
        """
        Calcular impacto en precio.
        """
        if "price" not in changes:
            return 0.0

        price_change = changes["price"]["difference"]
        return abs(float(price_change) / float(current_price))

    def _check_alternatives_needed(self, changes: Dict[str, Any]) -> bool:
        """
        Determinar si se necesitan alternativas.
        """
        severity = self._calculate_severity(changes)
        return severity >= 0.7

    def _determine_strategy(
        self, changes: Dict[str, Any], budget: Dict[str, Any]
    ) -> str:
        """
        Determinar mejor estrategia de reconstrucción.
        """
        severity = self._calculate_severity(changes)

        if severity >= 0.9:
            return ReconstructionStrategy.BEST_ALTERNATIVE
        elif severity >= 0.7:
            return ReconstructionStrategy.PRESERVE_PRICE
        elif severity >= 0.5:
            return ReconstructionStrategy.PRESERVE_MARGIN
        else:
            return ReconstructionStrategy.ADJUST_PROPORTIONALLY

    def _get_reconstruction_method(self, strategy: str):
        """
        Obtener método de reconstrucción según estrategia.
        """
        methods = {
            ReconstructionStrategy.PRESERVE_MARGIN: self._reconstruct_preserve_margin,
            ReconstructionStrategy.PRESERVE_PRICE: self._reconstruct_preserve_price,
            ReconstructionStrategy.ADJUST_PROPORTIONALLY: self._reconstruct_adjust_proportionally,
            ReconstructionStrategy.BEST_ALTERNATIVE: self._reconstruct_best_alternative,
        }
        return methods.get(strategy, self._reconstruct_adjust_proportionally)

    async def _reconstruct_preserve_margin(
        self, budget_id: str, changes: Dict[str, Any], impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reconstruir preservando el margen original.
        """
        budget = self.budget_manager._active_budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        original_margin = budget["margin"]
        updated_budget = budget.copy()

        if "price" in changes:
            new_base_price = Decimal(str(changes["price"]["current"]))
            updated_budget["base_price"] = new_base_price
            updated_budget["final_price"] = new_base_price * (1 + original_margin)

        updated_budget["metadata"]["margin_preserved"] = True
        updated_budget["modifications"].append(
            {
                "type": "margin_preservation",
                "timestamp": datetime.now().isoformat(),
                "changes": changes,
            }
        )

        return await self.budget_manager.update_budget(budget_id, updated_budget)

    async def _reconstruct_preserve_price(
        self, budget_id: str, changes: Dict[str, Any], impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reconstruir preservando el precio final.
        """
        budget = self.budget_manager._active_budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        original_final_price = budget["final_price"]
        updated_budget = budget.copy()

        if "price" in changes:
            new_base_price = Decimal(str(changes["price"]["current"]))
            updated_budget["base_price"] = new_base_price
            updated_budget["margin"] = (original_final_price / new_base_price) - 1

        updated_budget["metadata"]["price_preserved"] = True
        updated_budget["modifications"].append(
            {
                "type": "price_preservation",
                "timestamp": datetime.now().isoformat(),
                "changes": changes,
            }
        )

        return await self.budget_manager.update_budget(budget_id, updated_budget)

    async def _reconstruct_adjust_proportionally(
        self, budget_id: str, changes: Dict[str, Any], impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reconstruir ajustando proporcionalmente.
        """
        budget = self.budget_manager._active_budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        updated_budget = budget.copy()

        if "price" in changes:
            new_base_price = Decimal(str(changes["price"]["current"]))
            updated_budget["base_price"] = new_base_price
            updated_budget["final_price"] = new_base_price * (1 + budget["margin"])

        updated_budget["metadata"]["adjusted_proportionally"] = True
        updated_budget["modifications"].append(
            {
                "type": "proportional_adjustment",
                "timestamp": datetime.now().isoformat(),
                "changes": changes,
            }
        )

        return await self.budget_manager.update_budget(budget_id, updated_budget)

    async def _reconstruct_best_alternative(
        self, budget_id: str, changes: Dict[str, Any], impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reconstruir usando mejor alternativa disponible.
        """
        budget = self.budget_manager._active_budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Presupuesto {budget_id} no encontrado")

        alternatives = await self.suggest_alternatives(budget_id, changes)
        if not alternatives:
            return await self._reconstruct_preserve_price(budget_id, changes, impact)

        best_alternative = alternatives[0]
        updated_budget = budget.copy()

        updated_budget["package"] = best_alternative["package"]
        updated_budget["base_price"] = Decimal(
            str(best_alternative["package"]["price"])
        )
        updated_budget["final_price"] = updated_budget["base_price"] * (
            1 + budget["margin"]
        )

        updated_budget["metadata"]["alternative_selected"] = True
        updated_budget["metadata"]["original_package_id"] = budget["package"]["id"]
        updated_budget["modifications"].append(
            {
                "type": "alternative_selection",
                "timestamp": datetime.now().isoformat(),
                "changes": changes,
                "alternative_details": {
                    "similarity_score": best_alternative["similarity_score"],
                    "price_difference": best_alternative["price_difference"],
                },
            }
        )

        return await self.budget_manager.update_budget(budget_id, updated_budget)

    def _calculate_package_similarity(
        self, original: TravelPackage, alternative: TravelPackage
    ) -> float:
        """
        Calcular similitud entre paquetes (0-1).
        """
        score = 0.0
        weights = {
            "destination": 0.3,
            "duration": 0.2,
            "accommodation": 0.2,
            "price": 0.3,
        }

        # Similitud de destino
        if original.destination == alternative.destination:
            score += weights["destination"]

        # Similitud de duración
        duration_diff = abs(original.duration - alternative.duration)
        if duration_diff == 0:
            score += weights["duration"]
        elif duration_diff <= 1:
            score += weights["duration"] * 0.7
        elif duration_diff <= 2:
            score += weights["duration"] * 0.4

        # Similitud de alojamiento
        if original.accommodation.type == alternative.accommodation.type:
            score += weights["accommodation"] * 0.5
        if abs(original.accommodation.rating - alternative.accommodation.rating) <= 0.5:
            score += weights["accommodation"] * 0.5

        # Similitud de precio
        price_diff = abs(float(original.price - alternative.price))
        price_percentage = price_diff / float(original.price)
        if price_percentage <= 0.05:  # Diferencia <= 5%
            score += weights["price"]
        elif price_percentage <= 0.1:  # Diferencia <= 10%
            score += weights["price"] * 0.7
        elif price_percentage <= 0.15:  # Diferencia <= 15%
            score += weights["price"] * 0.4

        return score
