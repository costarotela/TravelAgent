"""Sistema de ejecución del agente."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

from src.core.database.base import db
from src.core.models.travel import TravelPackage, MarketAnalysis
from src.core.agent.planning import planning_system, ActionType, Action, Plan, PriorityLevel
from src.core.cache.redis_cache import cache

class ExecutionStatus(Enum):
    """Estados de ejecución."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExecutionResult(Enum):
    """Resultados de ejecución."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"

@dataclass
class TaskExecution:
    """Ejecución de una tarea."""
    action: Action
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime]
    result: Optional[ExecutionResult]
    impact: Optional[float]
    error: Optional[str]
    metadata: Dict[str, Any]

class ExecutionSystem:
    """Sistema de ejecución de acciones."""
    
    def __init__(self):
        self._active_executions: Dict[str, TaskExecution] = {}
        self._execution_history: List[TaskExecution] = []
        self._logger = logging.getLogger(__name__)
    
    async def execute_plan(
        self,
        origin: str,
        destination: str
    ) -> Tuple[ExecutionResult, List[TaskExecution]]:
        """Ejecutar plan para una ruta específica."""
        # Obtener plan
        plan = await planning_system.create_plan(origin, destination)
        if not plan:
            return ExecutionResult.FAILURE, []
        
        executions = []
        overall_success = True
        partial_success = False
        
        # Recrear acciones desde el plan
        actions = []
        for action_dict in plan.actions:
            action = Action(
                type=ActionType(action_dict["type"]),
                priority=PriorityLevel(action_dict["priority"]),
                route=action_dict["route"],
                description=action_dict["description"],
                expected_impact=action_dict["expected_impact"],
                deadline=datetime.fromisoformat(action_dict["deadline"]),
                context=action_dict["context"]
            )
            actions.append(action)
        
        # Ordenar acciones por prioridad
        sorted_actions = sorted(
            actions,
            key=lambda x: x.priority.value
        )
        
        for action in sorted_actions:
            execution = await self.execute_action(action, plan)
            executions.append(execution)
            
            if execution.result == ExecutionResult.SUCCESS:
                partial_success = True
            elif execution.result == ExecutionResult.FAILURE:
                overall_success = False
        
        # Determinar resultado general
        if overall_success and partial_success:
            return ExecutionResult.SUCCESS, executions
        elif partial_success:
            return ExecutionResult.PARTIAL, executions
        return ExecutionResult.FAILURE, executions
    
    async def execute_action(
        self,
        action: Action,
        plan: Plan
    ) -> TaskExecution:
        """Ejecutar una acción específica."""
        execution_key = f"{action.type.value}-{action.route[0]}-{action.route[1]}"
        
        # Verificar si ya existe una ejecución activa
        if execution_key in self._active_executions:
            existing = self._active_executions[execution_key]
            if existing.status in [ExecutionStatus.PENDING, ExecutionStatus.IN_PROGRESS]:
                return existing
        
        # Crear nueva ejecución
        execution = TaskExecution(
            action=action,
            status=ExecutionStatus.PENDING,
            start_time=datetime.utcnow(),
            end_time=None,
            result=None,
            impact=None,
            error=None,
            metadata={
                "market_status": plan.market_status,
                "risk_level": plan.risk_level,
                "confidence": plan.confidence
            }
        )
        
        self._active_executions[execution_key] = execution
        
        try:
            # Iniciar ejecución
            execution.status = ExecutionStatus.IN_PROGRESS
            
            # Ejecutar según tipo de acción
            if action.type == ActionType.PURCHASE:
                await self._execute_purchase(execution, plan)
            
            elif action.type == ActionType.SELL:
                await self._execute_sell(execution, plan)
            
            elif action.type == ActionType.ADJUST_PRICE:
                await self._execute_price_adjustment(execution, plan)
            
            elif action.type == ActionType.MONITOR:
                await self._execute_monitoring(execution, plan)
            
            elif action.type == ActionType.INVESTIGATE:
                await self._execute_investigation(execution, plan)
            
            elif action.type == ActionType.HOLD:
                await self._execute_hold(execution, plan)
            
            # Finalizar ejecución
            execution.status = ExecutionStatus.COMPLETED
            execution.end_time = datetime.utcnow()
            execution.result = ExecutionResult.SUCCESS
            
        except Exception as e:
            # Manejar error
            execution.status = ExecutionStatus.FAILED
            execution.end_time = datetime.utcnow()
            execution.result = ExecutionResult.FAILURE
            execution.error = str(e)
            self._logger.error(f"Error executing action: {str(e)}")
        
        # Guardar en historial
        self._execution_history.append(execution)
        
        # Limpiar ejecución activa
        if execution_key in self._active_executions:
            del self._active_executions[execution_key]
        
        return execution
    
    async def _execute_purchase(self, execution: TaskExecution, plan: Plan):
        """Ejecutar acción de compra."""
        action = execution.action
        
        # Simular proceso de compra
        await asyncio.sleep(1)  # Simular delay de red
        
        with db.get_session() as session:
            # Registrar intención de compra
            analysis = MarketAnalysis(
                origin=action.route[0],
                destination=action.route[1],
                avg_price=plan.metadata["avg_price"],
                min_price=plan.metadata["avg_price"] * 0.9,  # Simular
                max_price=plan.metadata["avg_price"] * 1.1,  # Simular
                demand_score=0.8 if plan.metadata["demand_trend"] == "high" else 0.5,
                trend="up" if plan.metadata["price_trend"] in ["bullish", "strongly_bullish"] else "down",
                analysis_date=datetime.utcnow(),
                data={
                    "action": "purchase",
                    "confidence": plan.confidence,
                    "risk_level": plan.risk_level
                }
            )
            session.add(analysis)
            session.commit()
        
        # Calcular impacto
        execution.impact = action.expected_impact * (plan.confidence * 0.8)
    
    async def _execute_sell(self, execution: TaskExecution, plan: Plan):
        """Ejecutar acción de venta."""
        action = execution.action
        
        # Simular proceso de venta
        await asyncio.sleep(1)  # Simular delay de red
        
        with db.get_session() as session:
            # Registrar intención de venta
            analysis = MarketAnalysis(
                origin=action.route[0],
                destination=action.route[1],
                avg_price=plan.metadata["avg_price"],
                min_price=plan.metadata["avg_price"] * 0.9,  # Simular
                max_price=plan.metadata["avg_price"] * 1.1,  # Simular
                demand_score=0.3 if plan.metadata["demand_trend"] == "low" else 0.5,
                trend="down" if plan.metadata["price_trend"] in ["bearish", "strongly_bearish"] else "up",
                analysis_date=datetime.utcnow(),
                data={
                    "action": "sell",
                    "confidence": plan.confidence,
                    "risk_level": plan.risk_level
                }
            )
            session.add(analysis)
            session.commit()
        
        # Calcular impacto
        execution.impact = action.expected_impact * (plan.confidence * 0.7)
    
    async def _execute_price_adjustment(self, execution: TaskExecution, plan: Plan):
        """Ejecutar ajuste de precios."""
        action = execution.action
        
        # Simular ajuste de precios
        await asyncio.sleep(0.5)  # Simular delay
        
        with db.get_session() as session:
            # Registrar ajuste
            analysis = MarketAnalysis(
                origin=action.route[0],
                destination=action.route[1],
                avg_price=plan.metadata["avg_price"],
                min_price=plan.metadata["avg_price"] * 0.95,  # Ajuste menor
                max_price=plan.metadata["avg_price"] * 1.05,  # Ajuste menor
                demand_score=0.6,  # Neutral
                trend="neutral",
                analysis_date=datetime.utcnow(),
                data={
                    "action": "price_adjustment",
                    "confidence": plan.confidence,
                    "risk_level": plan.risk_level
                }
            )
            session.add(analysis)
            session.commit()
        
        # Calcular impacto
        execution.impact = action.expected_impact * (plan.confidence * 0.9)
    
    async def _execute_monitoring(self, execution: TaskExecution, plan: Plan):
        """Ejecutar monitoreo de mercado."""
        action = execution.action
        
        # Simular monitoreo
        await asyncio.sleep(0.3)  # Simular delay
        
        # Registrar en caché para seguimiento
        monitor_key = f"monitor:{action.route[0]}-{action.route[1]}"
        await cache.set(
            monitor_key,
            {
                "last_check": datetime.utcnow().isoformat(),
                "frequency": action.context.get("check_frequency", "2h"),
                "market_status": plan.market_status,
                "risk_level": plan.risk_level
            },
            ttl=7200  # 2 horas
        )
        
        # Calcular impacto
        execution.impact = action.expected_impact * plan.confidence
    
    async def _execute_investigation(self, execution: TaskExecution, plan: Plan):
        """Ejecutar investigación de mercado."""
        action = execution.action
        
        # Simular investigación
        await asyncio.sleep(0.7)  # Simular delay
        
        with db.get_session() as session:
            # Registrar investigación
            analysis = MarketAnalysis(
                origin=action.route[0],
                destination=action.route[1],
                avg_price=plan.metadata["avg_price"],
                min_price=plan.metadata["avg_price"] * 0.8,  # Rango amplio
                max_price=plan.metadata["avg_price"] * 1.2,  # Rango amplio
                demand_score=0.5,  # Neutral
                trend="investigating",
                analysis_date=datetime.utcnow(),
                data={
                    "action": "investigation",
                    "confidence": plan.confidence,
                    "risk_level": plan.risk_level,
                    "volatility": plan.metadata["volatility"]
                }
            )
            session.add(analysis)
            session.commit()
        
        # Calcular impacto
        execution.impact = action.expected_impact * (plan.confidence * 0.6)
    
    async def _execute_hold(self, execution: TaskExecution, plan: Plan):
        """Ejecutar acción de mantener posición."""
        action = execution.action
        
        # Simular hold
        await asyncio.sleep(0.2)  # Simular delay mínimo
        
        # Registrar en caché
        hold_key = f"hold:{action.route[0]}-{action.route[1]}"
        await cache.set(
            hold_key,
            {
                "start_time": datetime.utcnow().isoformat(),
                "market_status": plan.market_status,
                "risk_level": plan.risk_level,
                "reason": "market_stability"
            },
            ttl=86400  # 24 horas
        )
        
        # Calcular impacto
        execution.impact = action.expected_impact * (plan.confidence * 0.5)

# Instancia global
execution_system = ExecutionSystem()
