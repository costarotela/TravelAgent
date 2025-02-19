"""
Orquestador del agente de viajes.

Este módulo se encarga de:
1. Coordinar flujos de trabajo
2. Gestionar eventos
3. Manejar estados
4. Supervisar componentes
"""

from typing import Dict, Any, Optional, List, Callable
import logging
import asyncio
from datetime import datetime
from enum import Enum

from .agent import SmartTravelAgent
from .agent_observer import AgentObserver
from .schemas import SearchCriteria, TravelPackage, Budget, AgentState, WorkflowState
from ..memory.supabase import SupabaseMemory


class WorkflowType(str, Enum):
    """Tipos de flujos de trabajo."""

    SEARCH = "search"
    BUDGET = "budget"
    BOOKING = "booking"
    MONITORING = "monitoring"


class AgentOrchestrator:
    """Orquestador del agente de viajes."""

    def __init__(self):
        """Inicializar orquestador."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Componentes principales
        self.agent = SmartTravelAgent()
        self.observer = AgentObserver()

        # Estado del orquestador
        self.active = False
        self.current_workflow: Optional[str] = None
        self.workflows: Dict[str, Dict[str, Any]] = {}

        # Manejadores de eventos
        self.event_handlers: Dict[str, List[Callable]] = {
            "workflow_started": [],
            "workflow_completed": [],
            "workflow_failed": [],
            "state_changed": [],
            "error_occurred": [],
        }

    async def start(self):
        """Iniciar orquestador."""
        try:
            self.active = True

            # Iniciar agente
            await self.agent.start()

            # Iniciar observador
            await self.observer.start(self.agent)

            # Iniciar monitores
            asyncio.create_task(self._monitor_workflows())

            self.logger.info("Orquestador iniciado")

        except Exception as e:
            self.logger.error(f"Error iniciando orquestador: {str(e)}")
            raise

    async def stop(self):
        """Detener orquestador."""
        try:
            self.active = False

            # Detener agente
            await self.agent.stop()

            # Detener observador
            await self.observer.stop()

            # Limpiar workflows activos
            for workflow_id in list(self.workflows.keys()):
                await self._cleanup_workflow(workflow_id)

            self.logger.info("Orquestador detenido")

        except Exception as e:
            self.logger.error(f"Error deteniendo orquestador: {str(e)}")
            raise

    async def execute_workflow(
        self,
        workflow_type: WorkflowType,
        params: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Ejecutar flujo de trabajo.

        Args:
            workflow_type: Tipo de flujo
            params: Parámetros del flujo
            metadata: Metadatos adicionales

        Returns:
            ID del flujo de trabajo
        """
        try:
            # Crear workflow
            workflow_id = f"{workflow_type.value}_{datetime.now().timestamp()}"

            workflow = {
                "id": workflow_id,
                "type": workflow_type,
                "params": params,
                "metadata": metadata or {},
                "state": WorkflowState.PENDING,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "result": None,
                "error": None,
            }

            self.workflows[workflow_id] = workflow

            # Notificar inicio
            await self._notify_event("workflow_started", {"workflow": workflow})

            # Ejecutar workflow
            asyncio.create_task(self._execute_workflow_task(workflow_id))

            return workflow_id

        except Exception as e:
            self.logger.error(f"Error ejecutando workflow: {str(e)}")
            raise

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Obtener estado de workflow.

        Args:
            workflow_id: ID del workflow

        Returns:
            Estado del workflow
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow no encontrado: {workflow_id}")

        return workflow

    def register_event_handler(self, event: str, handler: Callable):
        """
        Registrar manejador de eventos.

        Args:
            event: Nombre del evento
            handler: Función manejadora
        """
        if event not in self.event_handlers:
            raise ValueError(f"Evento no válido: {event}")

        self.event_handlers[event].append(handler)

    async def _execute_workflow_task(self, workflow_id: str):
        """Ejecutar tarea de workflow."""
        try:
            workflow = self.workflows[workflow_id]
            workflow["state"] = WorkflowState.RUNNING
            workflow["updated_at"] = datetime.now()

            # Ejecutar según tipo
            if workflow["type"] == WorkflowType.SEARCH:
                result = await self.agent.process_search(
                    criteria=SearchCriteria(**workflow["params"]["criteria"]),
                    metadata=workflow["metadata"],
                )

            elif workflow["type"] == WorkflowType.BUDGET:
                result = await self.agent.create_budget(
                    session_id=workflow["params"]["session_id"],
                    packages=[
                        TravelPackage(**p) for p in workflow["params"]["packages"]
                    ],
                    metadata=workflow["metadata"],
                )

            elif workflow["type"] == WorkflowType.BOOKING:
                result = await self.agent.process_booking(
                    session_id=workflow["params"]["session_id"],
                    budget_id=workflow["params"]["budget_id"],
                    metadata=workflow["metadata"],
                )

            elif workflow["type"] == WorkflowType.MONITORING:
                result = await self._execute_monitoring_workflow(workflow)

            # Actualizar workflow
            workflow["state"] = WorkflowState.COMPLETED
            workflow["result"] = result
            workflow["updated_at"] = datetime.now()

            # Notificar completado
            await self._notify_event("workflow_completed", {"workflow": workflow})

        except Exception as e:
            self.logger.error(f"Error en workflow {workflow_id}: {str(e)}")

            # Actualizar workflow
            workflow["state"] = WorkflowState.FAILED
            workflow["error"] = str(e)
            workflow["updated_at"] = datetime.now()

            # Notificar error
            await self._notify_event(
                "workflow_failed", {"workflow": workflow, "error": str(e)}
            )

    async def _execute_monitoring_workflow(
        self, workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ejecutar workflow de monitoreo."""
        try:
            session_id = workflow["params"]["session_id"]
            duration = workflow["params"].get("duration", 3600)  # 1 hora default
            interval = workflow["params"].get("interval", 300)  # 5 minutos default

            start_time = datetime.now()
            results = []

            while (datetime.now() - start_time).total_seconds() < duration:
                # Obtener estado actual
                session = await self.agent.session_manager.get_session(session_id)
                if not session:
                    break

                # Verificar cambios
                changes = await self._check_monitoring_changes(
                    session=session, previous_results=results
                )

                if changes:
                    results.append(
                        {"timestamp": datetime.now().isoformat(), "changes": changes}
                    )

                    # Notificar cambios
                    await self._notify_event(
                        "monitoring_changes",
                        {
                            "workflow_id": workflow["id"],
                            "session_id": session_id,
                            "changes": changes,
                        },
                    )

                await asyncio.sleep(interval)

            return {"results": results}

        except Exception as e:
            self.logger.error(f"Error en workflow de monitoreo: {str(e)}")
            raise

    async def _check_monitoring_changes(
        self, session: Dict[str, Any], previous_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Verificar cambios en monitoreo."""
        changes = {}

        # Verificar último resultado
        if not previous_results:
            return {"type": "initial_state", "data": session}

        last_result = previous_results[-1]

        # Verificar cambios en paquetes
        if "packages" in session:
            package_changes = self._detect_package_changes(
                current=session["packages"],
                previous=last_result["changes"].get("data", {}).get("packages", []),
            )
            if package_changes:
                changes["packages"] = package_changes

        # Verificar cambios en oportunidades
        if "opportunities" in session:
            opportunity_changes = self._detect_opportunity_changes(
                current=session["opportunities"],
                previous=last_result["changes"]
                .get("data", {})
                .get("opportunities", []),
            )
            if opportunity_changes:
                changes["opportunities"] = opportunity_changes

        return changes if changes else None

    def _detect_package_changes(
        self, current: List[Dict[str, Any]], previous: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detectar cambios en paquetes."""
        changes = {
            "price_changes": [],
            "availability_changes": [],
            "new_packages": [],
            "removed_packages": [],
        }

        current_ids = {p["id"] for p in current}
        previous_ids = {p["id"] for p in previous}

        # Nuevos paquetes
        new_ids = current_ids - previous_ids
        if new_ids:
            changes["new_packages"] = [p for p in current if p["id"] in new_ids]

        # Paquetes eliminados
        removed_ids = previous_ids - current_ids
        if removed_ids:
            changes["removed_packages"] = [
                p for p in previous if p["id"] in removed_ids
            ]

        # Cambios en paquetes existentes
        for curr_package in current:
            if curr_package["id"] in previous_ids:
                prev_package = next(
                    p for p in previous if p["id"] == curr_package["id"]
                )

                # Cambio de precio
                if curr_package["price"] != prev_package["price"]:
                    changes["price_changes"].append(
                        {
                            "package_id": curr_package["id"],
                            "old_price": prev_package["price"],
                            "new_price": curr_package["price"],
                        }
                    )

                # Cambio de disponibilidad
                if curr_package["availability"] != prev_package["availability"]:
                    changes["availability_changes"].append(
                        {
                            "package_id": curr_package["id"],
                            "old_availability": prev_package["availability"],
                            "new_availability": curr_package["availability"],
                        }
                    )

        return changes if any(changes.values()) else None

    def _detect_opportunity_changes(
        self, current: List[Dict[str, Any]], previous: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detectar cambios en oportunidades."""
        changes = {
            "new_opportunities": [],
            "expired_opportunities": [],
            "updated_opportunities": [],
        }

        current_ids = {o["id"] for o in current}
        previous_ids = {o["id"] for o in previous}

        # Nuevas oportunidades
        new_ids = current_ids - previous_ids
        if new_ids:
            changes["new_opportunities"] = [o for o in current if o["id"] in new_ids]

        # Oportunidades expiradas
        expired_ids = previous_ids - current_ids
        if expired_ids:
            changes["expired_opportunities"] = [
                o for o in previous if o["id"] in expired_ids
            ]

        # Cambios en oportunidades existentes
        for curr_opp in current:
            if curr_opp["id"] in previous_ids:
                prev_opp = next(o for o in previous if o["id"] == curr_opp["id"])

                if curr_opp != prev_opp:
                    changes["updated_opportunities"].append(
                        {
                            "opportunity_id": curr_opp["id"],
                            "old_state": prev_opp,
                            "new_state": curr_opp,
                        }
                    )

        return changes if any(changes.values()) else None

    async def _monitor_workflows(self):
        """Monitor de workflows."""
        while self.active:
            try:
                current_time = datetime.now()

                # Verificar workflows expirados
                for workflow_id, workflow in list(self.workflows.items()):
                    if workflow["state"] in [
                        WorkflowState.COMPLETED,
                        WorkflowState.FAILED,
                    ]:
                        # Limpiar después de 1 hora
                        if (
                            current_time - workflow["updated_at"]
                        ).total_seconds() > 3600:
                            await self._cleanup_workflow(workflow_id)

                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"Error en monitor de workflows: {str(e)}")
                await asyncio.sleep(60)

    async def _cleanup_workflow(self, workflow_id: str):
        """Limpiar workflow."""
        try:
            workflow = self.workflows.pop(workflow_id, None)
            if workflow:
                # Almacenar en histórico
                await self.memory.store_workflow_history(workflow)

        except Exception as e:
            self.logger.error(f"Error limpiando workflow: {str(e)}")

    async def _notify_event(self, event: str, data: Dict[str, Any]):
        """Notificar evento a manejadores."""
        try:
            handlers = self.event_handlers.get(event, [])
            for handler in handlers:
                try:
                    await handler(data)
                except Exception as e:
                    self.logger.error(f"Error en manejador de evento {event}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error notificando evento {event}: {str(e)}")
