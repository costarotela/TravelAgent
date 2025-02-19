"""
Sistema de eventos para presupuestos.

Este módulo maneja:
1. Emisión de eventos de presupuesto
2. Suscripción a eventos
3. Procesamiento de eventos
4. Registro de eventos
"""

from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
import logging
import asyncio
from dataclasses import dataclass
from prometheus_client import Counter, Histogram

# Métricas
EVENT_COUNTER = Counter(
    'budget_events_total',
    'Number of budget events processed',
    ['type']
)

EVENT_PROCESSING_TIME = Histogram(
    'event_processing_seconds',
    'Time spent processing events',
    ['type']
)

@dataclass
class EventMetadata:
    """Metadata de eventos."""
    timestamp: datetime
    source: str
    event_id: str
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None

class EventManager:
    """
    Gestor de eventos para presupuestos.
    """
    
    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._initialize_processors()

    def _initialize_processors(self):
        """Inicializar procesadores por defecto."""
        # Procesador para eventos de cambio
        self.subscribe(
            "budget_changed",
            self._process_budget_change
        )
        
        # Procesador para eventos de reconstrucción
        self.subscribe(
            "budget_reconstructed",
            self._process_reconstruction
        )
        
        # Procesador para eventos de alternativas
        self.subscribe(
            "alternatives_found",
            self._process_alternatives
        )

    def subscribe(
        self,
        event_type: str,
        handler: Callable
    ) -> None:
        """
        Suscribir handler a tipo de evento.
        
        Args:
            event_type: Tipo de evento
            handler: Función que maneja el evento
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable
    ) -> None:
        """
        Desuscribir handler de tipo de evento.
        
        Args:
            event_type: Tipo de evento
            handler: Función que maneja el evento
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    async def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emitir evento.
        
        Args:
            event_type: Tipo de evento
            data: Datos del evento
            metadata: Metadata opcional
        """
        event = {
            "type": event_type,
            "data": data,
            "metadata": EventMetadata(
                timestamp=datetime.now(),
                source="budget_system",
                event_id=f"evt_{datetime.now().timestamp()}",
                **(metadata or {})
            ).__dict__
        }
        
        await self._event_queue.put(event)
        
        # Iniciar procesamiento si no está corriendo
        if not self._processing_task or self._processing_task.done():
            self._processing_task = asyncio.create_task(
                self._process_events()
            )

    async def _process_events(self) -> None:
        """Procesar eventos en cola."""
        while True:
            try:
                event = await self._event_queue.get()
                
                start_time = datetime.now()
                
                # Procesar evento
                await self._dispatch_event(event)
                
                # Registrar métricas
                processing_time = (
                    datetime.now() - start_time
                ).total_seconds()
                
                EVENT_PROCESSING_TIME.labels(
                    type=event["type"]
                ).observe(processing_time)
                
                EVENT_COUNTER.labels(
                    type=event["type"]
                ).inc()
                
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error procesando evento: {e}")
                continue

    async def _dispatch_event(
        self,
        event: Dict[str, Any]
    ) -> None:
        """Distribuir evento a sus handlers."""
        event_type = event["type"]
        handlers = self._subscribers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                self.logger.error(
                    f"Error en handler {handler.__name__}: {e}"
                )

    async def _process_budget_change(
        self,
        event: Dict[str, Any]
    ) -> None:
        """
        Procesar evento de cambio en presupuesto.
        
        Coordina acciones necesarias cuando un presupuesto
        sufre modificaciones.
        """
        try:
            data = event["data"]
            metadata = event["metadata"]
            
            # Extraer información relevante
            budget_id = data.get("budget_id")
            changes = data.get("changes", {})
            timestamp = metadata["timestamp"]
            
            self.logger.info(
                f"Procesando cambios en presupuesto {budget_id}"
            )
            
            # Analizar severidad de cambios
            severity = self._calculate_change_severity(changes)
            
            # Registrar cambio en historial
            await self._record_event_history({
                "type": "budget_change",
                "budget_id": budget_id,
                "changes": changes,
                "severity": severity,
                "timestamp": timestamp
            })
            
            # Si hay cambios significativos, notificar
            if severity >= 0.7:  # 70% o más
                await self._notify_significant_change(
                    budget_id,
                    changes,
                    severity
                )
            
            # Actualizar métricas
            self._update_change_metrics(changes)
            
        except Exception as e:
            self.logger.error(
                f"Error procesando cambio en presupuesto: {e}"
            )
            raise

    async def _process_reconstruction(
        self,
        event: Dict[str, Any]
    ) -> None:
        """
        Procesar evento de reconstrucción.
        
        Coordina acciones cuando un presupuesto ha sido
        reconstruido.
        """
        try:
            data = event["data"]
            metadata = event["metadata"]
            
            # Extraer información relevante
            budget_id = data.get("budget_id")
            strategy = data.get("strategy_used")
            impact = data.get("impact", {})
            timestamp = metadata["timestamp"]
            
            self.logger.info(
                f"Procesando reconstrucción de presupuesto {budget_id}"
            )
            
            # Registrar reconstrucción
            await self._record_event_history({
                "type": "reconstruction",
                "budget_id": budget_id,
                "strategy": strategy,
                "impact": impact,
                "timestamp": timestamp
            })
            
            # Actualizar métricas de reconstrucción
            self._update_reconstruction_metrics(strategy, impact)
            
            # Notificar resultado
            await self._notify_reconstruction_result(
                budget_id,
                strategy,
                impact
            )
            
        except Exception as e:
            self.logger.error(
                f"Error procesando reconstrucción: {e}"
            )
            raise

    async def _process_alternatives(
        self,
        event: Dict[str, Any]
    ) -> None:
        """
        Procesar evento de alternativas encontradas.
        
        Coordina acciones cuando se encuentran alternativas
        para un presupuesto.
        """
        try:
            data = event["data"]
            metadata = event["metadata"]
            
            # Extraer información relevante
            budget_id = data.get("budget_id")
            alternatives = data.get("alternatives", [])
            reason = data.get("reason")
            timestamp = metadata["timestamp"]
            
            self.logger.info(
                f"Procesando alternativas para presupuesto {budget_id}"
            )
            
            # Registrar búsqueda de alternativas
            await self._record_event_history({
                "type": "alternatives_found",
                "budget_id": budget_id,
                "count": len(alternatives),
                "reason": reason,
                "timestamp": timestamp
            })
            
            # Actualizar métricas
            self._update_alternatives_metrics(
                len(alternatives),
                reason
            )
            
            # Notificar si hay alternativas viables
            if alternatives:
                await self._notify_alternatives_found(
                    budget_id,
                    alternatives,
                    reason
                )
            
        except Exception as e:
            self.logger.error(
                f"Error procesando alternativas: {e}"
            )
            raise

    def _calculate_change_severity(
        self,
        changes: Dict[str, Any]
    ) -> float:
        """Calcular severidad de cambios."""
        severity = 0.0
        weights = {
            "price": 0.6,
            "availability": 0.2,
            "dates": 0.1,
            "features": 0.1
        }
        
        for field, weight in weights.items():
            if field in changes:
                severity += weight
                
        return min(severity, 1.0)

    def _update_change_metrics(
        self,
        changes: Dict[str, Any]
    ) -> None:
        """Actualizar métricas de cambios."""
        for field in changes:
            EVENT_COUNTER.labels(
                type=f"change_{field}"
            ).inc()

    def _update_reconstruction_metrics(
        self,
        strategy: str,
        impact: Dict[str, Any]
    ) -> None:
        """Actualizar métricas de reconstrucción."""
        EVENT_COUNTER.labels(
            type=f"reconstruction_{strategy}"
        ).inc()

    def _update_alternatives_metrics(
        self,
        count: int,
        reason: str
    ) -> None:
        """Actualizar métricas de alternativas."""
        EVENT_COUNTER.labels(
            type=f"alternatives_{reason}"
        ).inc()

    async def _notify_significant_change(
        self,
        budget_id: str,
        changes: Dict[str, Any],
        severity: float
    ) -> None:
        """Notificar cambios significativos."""
        # TODO: Integrar con sistema de notificaciones
        self.logger.warning(
            f"Cambio significativo en presupuesto {budget_id}"
            f" (severidad: {severity})"
        )

    async def _notify_reconstruction_result(
        self,
        budget_id: str,
        strategy: str,
        impact: Dict[str, Any]
    ) -> None:
        """Notificar resultado de reconstrucción."""
        # TODO: Integrar con sistema de notificaciones
        self.logger.info(
            f"Reconstrucción completada para presupuesto {budget_id}"
            f" usando estrategia {strategy}"
        )

    async def _notify_alternatives_found(
        self,
        budget_id: str,
        alternatives: List[Dict[str, Any]],
        reason: str
    ) -> None:
        """Notificar alternativas encontradas."""
        # TODO: Integrar con sistema de notificaciones
        self.logger.info(
            f"Encontradas {len(alternatives)} alternativas"
            f" para presupuesto {budget_id}"
        )

    async def _record_event_history(
        self,
        event_data: Dict[str, Any]
    ) -> None:
        """Registrar evento en historial."""
        # TODO: Implementar persistencia real
        self.logger.debug(f"Evento registrado: {event_data}")

# Instancia global
event_manager = EventManager()

async def get_event_manager() -> EventManager:
    """Obtener instancia única del gestor."""
    return event_manager
