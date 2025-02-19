"""
Integración entre sistemas de presupuestos.

Este módulo maneja:
1. Integración entre eventos y notificaciones
2. Coordinación de acciones entre sistemas
3. Métricas unificadas
4. Registro centralizado
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from prometheus_client import Counter, Histogram

from .events import get_event_manager, EventManager
from .notifications import get_notification_manager, NotificationManager
from .reconstruction import get_reconstruction_manager, BudgetReconstructionManager

# Métricas de integración
INTEGRATION_OPERATIONS = Counter(
    'budget_integration_operations_total',
    'Number of integration operations',
    ['operation_type']
)

INTEGRATION_LATENCY = Histogram(
    'integration_operation_latency_seconds',
    'Latency of integration operations',
    ['operation_type']
)

class BudgetSystemIntegrator:
    """
    Integrador de sistemas de presupuestos.
    
    Coordina la interacción entre:
    - Sistema de eventos
    - Sistema de notificaciones
    - Sistema de reconstrucción
    """
    
    def __init__(self):
        """Inicializar integrador."""
        self.logger = logging.getLogger(__name__)
        self._initialize_managers()
        self._setup_event_handlers()
        self._setup_notification_handlers()

    async def _initialize_managers(self):
        """Inicializar gestores."""
        self.events = await get_event_manager()
        self.notifications = await get_notification_manager()
        self.reconstruction = await get_reconstruction_manager()

    def _setup_event_handlers(self):
        """Configurar handlers de eventos."""
        # Eventos de cambio
        self.events.subscribe(
            "budget_changed",
            self._handle_budget_change_event
        )
        
        # Eventos de reconstrucción
        self.events.subscribe(
            "budget_reconstructed",
            self._handle_reconstruction_event
        )
        
        # Eventos de alternativas
        self.events.subscribe(
            "alternatives_found",
            self._handle_alternatives_event
        )

    def _setup_notification_handlers(self):
        """Configurar handlers de notificaciones."""
        # Notificaciones de precio
        self.notifications.register_handler(
            "price",
            self._handle_price_notification
        )
        
        # Notificaciones de disponibilidad
        self.notifications.register_handler(
            "availability",
            self._handle_availability_notification
        )
        
        # Notificaciones de reconstrucción
        self.notifications.register_handler(
            "reconstruction",
            self._handle_reconstruction_notification
        )

    async def _handle_budget_change_event(
        self,
        event: Dict[str, Any]
    ) -> None:
        """
        Manejar evento de cambio en presupuesto.
        
        Coordina:
        1. Análisis de impacto
        2. Notificaciones necesarias
        3. Reconstrucción si es necesario
        """
        try:
            start_time = datetime.now()
            
            data = event["data"]
            budget_id = data["budget_id"]
            changes = data["changes"]
            
            # Analizar impacto
            impact = await self.reconstruction.analyze_impact(
                budget_id,
                changes
            )
            
            # Determinar si requiere reconstrucción
            if impact.impact_level >= 0.7:  # Impacto alto
                await self.notifications.notify(
                    "reconstruction_needed",
                    {
                        "budget_id": budget_id,
                        "reason": "high_impact_changes",
                        "impact_level": impact.impact_level
                    }
                )
                
                # Iniciar reconstrucción
                await self.reconstruction.reconstruct_budget(
                    budget_id,
                    changes
                )
            
            # Notificar cambios significativos
            if "price" in changes:
                await self.notifications.notify(
                    "price_change",
                    {
                        "package_id": data.get("package_id"),
                        "percentage": changes["price"].get("percentage")
                    }
                )
            
            duration = (datetime.now() - start_time).total_seconds()
            INTEGRATION_LATENCY.labels(
                operation_type="budget_change"
            ).observe(duration)
            
        except Exception as e:
            self.logger.error(
                f"Error manejando cambio en presupuesto: {e}"
            )
            raise

    async def _handle_reconstruction_event(
        self,
        event: Dict[str, Any]
    ) -> None:
        """
        Manejar evento de reconstrucción.
        
        Coordina:
        1. Notificación de resultado
        2. Búsqueda de alternativas si es necesario
        3. Actualización de estado
        """
        try:
            start_time = datetime.now()
            
            data = event["data"]
            budget_id = data["budget_id"]
            strategy = data["strategy_used"]
            impact = data["impact"]
            
            # Notificar resultado
            await self.notifications.notify(
                "reconstruction_complete",
                {
                    "budget_id": budget_id,
                    "strategy": strategy
                }
            )
            
            # Si el impacto sigue siendo alto, buscar alternativas
            if impact.get("impact_level", 0) >= 0.9:
                alternatives = await self.reconstruction.suggest_alternatives(
                    budget_id,
                    impact.get("changes", {})
                )
                
                if alternatives:
                    await self.notifications.notify(
                        "alternatives_found",
                        {
                            "budget_id": budget_id,
                            "count": len(alternatives)
                        }
                    )
            
            duration = (datetime.now() - start_time).total_seconds()
            INTEGRATION_LATENCY.labels(
                operation_type="reconstruction"
            ).observe(duration)
            
        except Exception as e:
            self.logger.error(
                f"Error manejando reconstrucción: {e}"
            )
            raise

    async def _handle_alternatives_event(
        self,
        event: Dict[str, Any]
    ) -> None:
        """
        Manejar evento de alternativas encontradas.
        
        Coordina:
        1. Notificación de alternativas
        2. Actualización de estado
        """
        try:
            start_time = datetime.now()
            
            data = event["data"]
            budget_id = data["budget_id"]
            alternatives = data["alternatives"]
            
            # Notificar alternativas encontradas
            await self.notifications.notify(
                "alternatives_found",
                {
                    "budget_id": budget_id,
                    "count": len(alternatives)
                }
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            INTEGRATION_LATENCY.labels(
                operation_type="alternatives"
            ).observe(duration)
            
        except Exception as e:
            self.logger.error(
                f"Error manejando alternativas: {e}"
            )
            raise

    async def _handle_price_notification(
        self,
        notification: Dict[str, Any]
    ) -> None:
        """
        Procesar notificación de precio.
        
        Coordina:
        1. Análisis de impacto en sesiones activas
        2. Actualización de precios si es apropiado
        3. Registro de cambios
        """
        try:
            INTEGRATION_OPERATIONS.labels(
                operation_type="price_notification"
            ).inc()
            
            data = notification["data"]
            package_id = data["package_id"]
            price_change = data["price_change"]
            
            # Verificar sesiones activas que usan este paquete
            active_sessions = await self.events.get_active_sessions_with_package(
                package_id
            )
            
            for session in active_sessions:
                # Analizar impacto en la sesión
                impact = await self.reconstruction.analyze_session_impact(
                    session["id"],
                    {"price_change": price_change}
                )
                
                # Si la sesión está activa, posponer cambios
                if session.get("status") == "active":
                    await self.events.emit(
                        "price_change_queued",
                        {
                            "session_id": session["id"],
                            "package_id": package_id,
                            "price_change": price_change,
                            "impact": impact
                        }
                    )
                    continue
                
                # Para sesiones no activas, aplicar cambios
                if impact.impact_level >= 0.5:  # Impacto significativo
                    await self.reconstruction.reconstruct_budget(
                        session["id"],
                        {"price_change": price_change}
                    )
                    
                    await self.notifications.notify(
                        "budget_reconstructed",
                        {
                            "session_id": session["id"],
                            "reason": "price_change",
                            "impact_level": impact.impact_level
                        }
                    )
            
        except Exception as e:
            self.logger.error(f"Error procesando notificación de precio: {e}")
            raise

    async def _handle_availability_notification(
        self,
        notification: Dict[str, Any]
    ) -> None:
        """
        Procesar notificación de disponibilidad.
        
        Coordina:
        1. Verificación de impacto en presupuestos
        2. Búsqueda de alternativas si es necesario
        3. Notificaciones apropiadas
        """
        try:
            INTEGRATION_OPERATIONS.labels(
                operation_type="availability_notification"
            ).inc()
            
            data = notification["data"]
            package_id = data["package_id"]
            availability = data["availability"]
            
            # Verificar presupuestos afectados
            affected_budgets = await self.events.get_budgets_with_package(
                package_id
            )
            
            for budget in affected_budgets:
                # Si no hay disponibilidad, buscar alternativas
                if availability["status"] == "unavailable":
                    alternatives = await self.reconstruction.suggest_alternatives(
                        budget["id"],
                        {"availability": availability}
                    )
                    
                    if alternatives:
                        await self.notifications.notify(
                            "alternatives_found",
                            {
                                "budget_id": budget["id"],
                                "original_package": package_id,
                                "alternatives_count": len(alternatives)
                            }
                        )
                    else:
                        await self.notifications.notify(
                            "no_alternatives",
                            {
                                "budget_id": budget["id"],
                                "package_id": package_id
                            }
                        )
                
                # Si hay cambios en disponibilidad pero sigue disponible
                elif availability["status"] == "limited":
                    await self.notifications.notify(
                        "availability_warning",
                        {
                            "budget_id": budget["id"],
                            "package_id": package_id,
                            "remaining": availability.get("remaining", 0)
                        }
                    )
            
        except Exception as e:
            self.logger.error(
                f"Error procesando notificación de disponibilidad: {e}"
            )
            raise

    async def _handle_reconstruction_notification(
        self,
        notification: Dict[str, Any]
    ) -> None:
        """
        Procesar notificación de reconstrucción.
        
        Coordina:
        1. Registro de reconstrucción
        2. Notificaciones de resultado
        3. Métricas de reconstrucción
        """
        try:
            INTEGRATION_OPERATIONS.labels(
                operation_type="reconstruction_notification"
            ).inc()
            
            data = notification["data"]
            budget_id = data["budget_id"]
            strategy = data.get("strategy", "unknown")
            success = data.get("success", False)
            
            # Registrar resultado
            await self.events.emit(
                "reconstruction_completed",
                {
                    "budget_id": budget_id,
                    "strategy": strategy,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Si la reconstrucción fue exitosa
            if success:
                # Obtener detalles del resultado
                result = await self.reconstruction.get_reconstruction_details(
                    budget_id
                )
                
                # Notificar cambios significativos
                if result.get("price_difference"):
                    await self.notifications.notify(
                        "price_changed_after_reconstruction",
                        {
                            "budget_id": budget_id,
                            "difference": result["price_difference"],
                            "percentage": result["price_difference_percentage"]
                        }
                    )
                
                if result.get("alternatives_used"):
                    await self.notifications.notify(
                        "alternatives_applied",
                        {
                            "budget_id": budget_id,
                            "original_packages": result["original_packages"],
                            "new_packages": result["new_packages"]
                        }
                    )
            
            # Si la reconstrucción falló
            else:
                await self.notifications.notify(
                    "reconstruction_failed",
                    {
                        "budget_id": budget_id,
                        "reason": data.get("error", "unknown_error"),
                        "strategy": strategy
                    }
                )
            
        except Exception as e:
            self.logger.error(
                f"Error procesando notificación de reconstrucción: {e}"
            )
            raise

# Instancia global
budget_integrator = BudgetSystemIntegrator()

async def get_budget_integrator() -> BudgetSystemIntegrator:
    """Obtener instancia única del integrador."""
    return budget_integrator
