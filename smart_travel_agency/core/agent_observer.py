"""
Observador del agente de viajes.

Este módulo se encarga de:
1. Monitorear el estado del agente
2. Registrar eventos y acciones
3. Generar métricas
4. Detectar anomalías
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from .agent import SmartTravelAgent
from .schemas import AgentState, AgentMetrics
from ..memory.supabase import SupabaseMemory


class AgentObserver:
    """Observador del agente de viajes."""

    def __init__(self):
        """Inicializar observador."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Estado del observador
        self.active = False
        self.agent: Optional[SmartTravelAgent] = None
        self.last_check = datetime.now()

        # Métricas
        self.metrics: Dict[str, Any] = {
            "sessions": {"total": 0, "active": 0, "completed": 0, "failed": 0},
            "searches": {"total": 0, "successful": 0, "failed": 0, "avg_duration": 0},
            "packages": {"total": 0, "analyzed": 0, "recommended": 0},
            "opportunities": {"total": 0, "active": 0, "converted": 0},
            "budgets": {"total": 0, "approved": 0, "rejected": 0},
        }

        # Configuración
        self.check_interval = 60  # 1 minuto
        self.metrics_interval = 300  # 5 minutos
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10% de errores
            "response_time": 5.0,  # 5 segundos
            "memory_usage": 0.8,  # 80% de uso
        }

    async def start(self, agent: SmartTravelAgent):
        """
        Iniciar observador.

        Args:
            agent: Agente a observar
        """
        try:
            self.active = True
            self.agent = agent

            # Iniciar monitores
            asyncio.create_task(self._monitor_agent())
            asyncio.create_task(self._collect_metrics())

            self.logger.info("Observador iniciado")

        except Exception as e:
            self.logger.error(f"Error iniciando observador: {str(e)}")
            raise

    async def stop(self):
        """Detener observador."""
        try:
            self.active = False

            # Almacenar métricas finales
            await self._store_metrics()

            self.logger.info("Observador detenido")

        except Exception as e:
            self.logger.error(f"Error deteniendo observador: {str(e)}")
            raise

    async def get_agent_state(self) -> AgentState:
        """
        Obtener estado actual del agente.

        Returns:
            Estado actual del agente
        """
        try:
            if not self.agent:
                raise ValueError("Agente no inicializado")

            # Obtener métricas actuales
            metrics = await self._get_current_metrics()

            # Verificar estado de componentes
            components_status = await self._check_components()

            # Crear estado
            state = AgentState(
                active=self.agent.active,
                current_session=self.agent.current_session,
                last_update=self.agent.last_update,
                metrics=metrics,
                components=components_status,
            )

            return state

        except Exception as e:
            self.logger.error(f"Error obteniendo estado: {str(e)}")
            raise

    async def get_metrics(self, metric_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtener métricas del agente.

        Args:
            metric_type: Tipo específico de métrica

        Returns:
            Métricas solicitadas
        """
        try:
            if metric_type:
                if metric_type not in self.metrics:
                    raise ValueError(f"Tipo de métrica no válido: {metric_type}")
                return {metric_type: self.metrics[metric_type]}

            return self.metrics

        except Exception as e:
            self.logger.error(f"Error obteniendo métricas: {str(e)}")
            raise

    async def _monitor_agent(self):
        """Monitor continuo del agente."""
        while self.active:
            try:
                if not self.agent:
                    raise ValueError("Agente no inicializado")

                # Verificar estado
                state = await self.get_agent_state()

                # Detectar anomalías
                alerts = await self._detect_anomalies(state)

                # Procesar alertas
                if alerts:
                    await self._process_alerts(alerts)

                self.last_check = datetime.now()
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error monitoreando agente: {str(e)}")
                await asyncio.sleep(60)

    async def _collect_metrics(self):
        """Recolectar métricas periódicamente."""
        while self.active:
            try:
                if not self.agent:
                    raise ValueError("Agente no inicializado")

                # Actualizar métricas
                await self._update_metrics()

                # Almacenar métricas
                await self._store_metrics()

                await asyncio.sleep(self.metrics_interval)

            except Exception as e:
                self.logger.error(f"Error recolectando métricas: {str(e)}")
                await asyncio.sleep(60)

    async def _update_metrics(self):
        """Actualizar métricas del agente."""
        try:
            if not self.agent:
                raise ValueError("Agente no inicializado")

            # Obtener sesiones activas
            active_sessions = len(self.agent.session_manager.active_sessions)

            # Actualizar métricas de sesiones
            self.metrics["sessions"]["active"] = active_sessions

            # Obtener métricas de componentes
            component_metrics = await self._get_component_metrics()

            # Actualizar métricas
            self.metrics.update(component_metrics)

        except Exception as e:
            self.logger.error(f"Error actualizando métricas: {str(e)}")
            raise

    async def _store_metrics(self):
        """Almacenar métricas en base de conocimiento."""
        try:
            metrics = AgentMetrics(timestamp=datetime.now(), metrics=self.metrics)

            await self.memory.store_metrics(metrics.dict())

        except Exception as e:
            self.logger.error(f"Error almacenando métricas: {str(e)}")
            raise

    async def _get_current_metrics(self) -> Dict[str, Any]:
        """Obtener métricas actuales."""
        try:
            # Obtener métricas de rendimiento
            performance_metrics = {
                "response_time": await self._get_avg_response_time(),
                "error_rate": await self._get_error_rate(),
                "memory_usage": await self._get_memory_usage(),
            }

            # Combinar con métricas generales
            return {**self.metrics, "performance": performance_metrics}

        except Exception as e:
            self.logger.error(f"Error obteniendo métricas actuales: {str(e)}")
            raise

    async def _check_components(self) -> Dict[str, bool]:
        """Verificar estado de componentes."""
        try:
            if not self.agent:
                raise ValueError("Agente no inicializado")

            return {
                "session_manager": self.agent.session_manager is not None,
                "analyzer": self.agent.analyzer is not None,
                "price_monitor": self.agent.price_monitor is not None,
                "opportunity_tracker": self.agent.opportunity_tracker is not None,
                "recommendation_engine": self.agent.recommendation_engine is not None,
                "browser_manager": self.agent.browser_manager is not None,
                "provider_manager": self.agent.provider_manager is not None,
                "budget_engine": self.agent.budget_engine is not None,
                "storage": self.agent.storage is not None,
            }

        except Exception as e:
            self.logger.error(f"Error verificando componentes: {str(e)}")
            raise

    async def _detect_anomalies(self, state: AgentState) -> List[Dict[str, Any]]:
        """Detectar anomalías en estado del agente."""
        alerts = []

        try:
            # Verificar tasa de errores
            if (
                state.metrics["performance"]["error_rate"]
                > self.alert_thresholds["error_rate"]
            ):
                alerts.append(
                    {
                        "type": "high_error_rate",
                        "value": state.metrics["performance"]["error_rate"],
                        "threshold": self.alert_thresholds["error_rate"],
                    }
                )

            # Verificar tiempo de respuesta
            if (
                state.metrics["performance"]["response_time"]
                > self.alert_thresholds["response_time"]
            ):
                alerts.append(
                    {
                        "type": "high_response_time",
                        "value": state.metrics["performance"]["response_time"],
                        "threshold": self.alert_thresholds["response_time"],
                    }
                )

            # Verificar uso de memoria
            if (
                state.metrics["performance"]["memory_usage"]
                > self.alert_thresholds["memory_usage"]
            ):
                alerts.append(
                    {
                        "type": "high_memory_usage",
                        "value": state.metrics["performance"]["memory_usage"],
                        "threshold": self.alert_thresholds["memory_usage"],
                    }
                )

            return alerts

        except Exception as e:
            self.logger.error(f"Error detectando anomalías: {str(e)}")
            return []

    async def _process_alerts(self, alerts: List[Dict[str, Any]]):
        """Procesar alertas detectadas."""
        try:
            for alert in alerts:
                # Registrar alerta
                self.logger.warning(
                    f"Alerta: {alert['type']} - "
                    f"Valor: {alert['value']} - "
                    f"Umbral: {alert['threshold']}"
                )

                # Almacenar alerta
                await self.memory.store_alert(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "type": alert["type"],
                        "value": alert["value"],
                        "threshold": alert["threshold"],
                    }
                )

        except Exception as e:
            self.logger.error(f"Error procesando alertas: {str(e)}")
            raise

    async def _get_component_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de componentes."""
        try:
            if not self.agent:
                raise ValueError("Agente no inicializado")

            return {
                "analyzer": {
                    "packages_analyzed": len(
                        await self.agent.analyzer.get_analyzed_packages()
                    )
                },
                "price_monitor": {
                    "active_monitors": len(
                        await self.agent.price_monitor.get_active_monitors()
                    )
                },
                "opportunity_tracker": {
                    "active_opportunities": len(
                        await self.agent.opportunity_tracker.get_active_opportunities()
                    )
                },
                "recommendation_engine": {
                    "recommendations_made": len(
                        await self.agent.recommendation_engine.get_recommendations_history()
                    )
                },
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo métricas de componentes: {str(e)}")
            return {}

    async def _get_avg_response_time(self) -> float:
        """Obtener tiempo de respuesta promedio."""
        try:
            # Implementar cálculo de tiempo de respuesta
            return 0.0

        except Exception as e:
            self.logger.error(f"Error obteniendo tiempo de respuesta: {str(e)}")
            return 0.0

    async def _get_error_rate(self) -> float:
        """Obtener tasa de errores."""
        try:
            # Implementar cálculo de tasa de errores
            return 0.0

        except Exception as e:
            self.logger.error(f"Error obteniendo tasa de errores: {str(e)}")
            return 0.0

    async def _get_memory_usage(self) -> float:
        """Obtener uso de memoria."""
        try:
            # Implementar cálculo de uso de memoria
            return 0.0

        except Exception as e:
            self.logger.error(f"Error obteniendo uso de memoria: {str(e)}")
            return 0.0
