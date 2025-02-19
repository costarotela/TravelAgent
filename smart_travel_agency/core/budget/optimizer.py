"""
Optimizador de presupuestos.

Este módulo implementa:
1. Optimización iterativa de presupuestos
2. Balanceo de objetivos comerciales
3. Adaptación a condiciones de mercado
4. Mantenimiento de estabilidad
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from decimal import Decimal
from prometheus_client import Counter, Histogram

from ..schemas import (
    Budget,
    TravelPackage,
    OptimizationGoal,
    OptimizationConstraint,
    OptimizationResult,
    SessionState
)
from ..metrics import get_metrics_collector
from ..memory import get_memory_manager

# Métricas
OPTIMIZATION_OPERATIONS = Counter(
    'budget_optimization_operations_total',
    'Number of optimization operations',
    ['operation_type']
)

OPTIMIZATION_LATENCY = Histogram(
    'optimization_operation_latency_seconds',
    'Latency of optimization operations',
    ['operation_type']
)

class BudgetOptimizer:
    """
    Optimizador de presupuestos.
    
    Responsabilidades:
    1. Optimizar presupuestos iterativamente
    2. Mantener equilibrio entre objetivos
    3. Preservar estabilidad de sesiones
    """

    def __init__(self):
        """Inicializar optimizador."""
        self.logger = logging.getLogger(__name__)
        self.memory = get_memory_manager()
        self.metrics = get_metrics_collector()
        
        # Configuración de optimización
        self.config = {
            "max_iterations": 3,      # Máximo de iteraciones
            "convergence_threshold": 0.01,  # 1% de cambio mínimo
            "stability_threshold": 0.8,     # 80% de estabilidad mínima
            "price_flexibility": 0.15,      # 15% de flexibilidad en precios
            "margin_flexibility": 0.1       # 10% de flexibilidad en márgenes
        }
        
        # Objetivos de optimización
        self.goals = {
            OptimizationGoal.MAXIMIZE_MARGIN: self._optimize_for_margin,
            OptimizationGoal.MAXIMIZE_COMPETITIVENESS: self._optimize_for_competitiveness,
            OptimizationGoal.BALANCE_PRICE_QUALITY: self._optimize_for_balance
        }

    async def optimize_budget(
        self,
        budget: Budget,
        goal: OptimizationGoal,
        constraints: Optional[List[OptimizationConstraint]] = None,
        session_state: Optional[SessionState] = None
    ) -> OptimizationResult:
        """
        Optimizar presupuesto según objetivo.
        
        Args:
            budget: Presupuesto a optimizar
            goal: Objetivo de optimización
            constraints: Restricciones a considerar
            session_state: Estado de sesión activa
            
        Returns:
            Resultado de la optimización
        """
        try:
            start_time = datetime.now()
            
            # Si hay sesión activa, validar estabilidad
            if session_state and session_state.is_active:
                stability_score = self._calculate_stability_impact(
                    budget,
                    goal
                )
                
                if stability_score < self.config["stability_threshold"]:
                    return OptimizationResult(
                        success=False,
                        error="optimization_too_disruptive",
                        stability_score=stability_score
                    )
            
            # Inicializar resultado
            current_budget = budget.copy()
            best_score = self._calculate_score(current_budget, goal)
            best_budget = current_budget
            
            # Optimización iterativa
            for iteration in range(self.config["max_iterations"]):
                # Aplicar estrategia de optimización
                optimize_func = self.goals[goal]
                optimized_budget = await optimize_func(
                    current_budget,
                    constraints
                )
                
                # Calcular nuevo score
                new_score = self._calculate_score(optimized_budget, goal)
                
                # Verificar mejora
                if new_score > best_score:
                    improvement = (new_score - best_score) / best_score
                    
                    # Verificar convergencia
                    if improvement < self.config["convergence_threshold"]:
                        break
                        
                    best_score = new_score
                    best_budget = optimized_budget
                
                current_budget = optimized_budget
            
            # Validar resultado
            if not self._validate_optimization(best_budget, constraints):
                return OptimizationResult(
                    success=False,
                    error="invalid_optimization"
                )
            
            # Registrar métricas
            duration = (datetime.now() - start_time).total_seconds()
            OPTIMIZATION_LATENCY.labels(
                operation_type=goal.value
            ).observe(duration)
            
            OPTIMIZATION_OPERATIONS.labels(
                operation_type=goal.value
            ).inc()
            
            return OptimizationResult(
                success=True,
                optimized_budget=best_budget,
                score=best_score,
                iterations_used=iteration + 1,
                metadata={
                    "goal": goal.value,
                    "optimization_time": duration,
                    "improvement": (best_score - self._calculate_score(budget, goal)) / self._calculate_score(budget, goal)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error en optimización: {e}")
            return OptimizationResult(
                success=False,
                error=str(e)
            )

    async def _optimize_for_margin(
        self,
        budget: Budget,
        constraints: Optional[List[OptimizationConstraint]]
    ) -> Budget:
        """Optimizar para maximizar margen."""
        try:
            optimized = budget.copy()
            
            # Obtener datos de mercado
            market_data = await self.memory.get_market_data(
                [pkg.id for pkg in optimized.packages]
            )
            
            for package in optimized.packages:
                if package.id in market_data:
                    pkg_data = market_data[package.id]
                    
                    # Calcular margen máximo posible
                    max_price = pkg_data["max_market_price"]
                    current_cost = package.cost
                    
                    # Ajustar precio manteniendo competitividad
                    new_price = min(
                        max_price,
                        current_cost * (1 + self.config["margin_flexibility"])
                    )
                    
                    package.price = new_price
            
            return optimized
            
        except Exception as e:
            self.logger.error(f"Error optimizando margen: {e}")
            raise

    async def _optimize_for_competitiveness(
        self,
        budget: Budget,
        constraints: Optional[List[OptimizationConstraint]]
    ) -> Budget:
        """Optimizar para maximizar competitividad."""
        try:
            optimized = budget.copy()
            
            # Obtener precios competitivos
            market_prices = await self.memory.get_market_prices(
                [pkg.id for pkg in optimized.packages]
            )
            
            for package in optimized.packages:
                if package.id in market_prices:
                    market_price = market_prices[package.id]
                    
                    # Ajustar precio para ser competitivo
                    new_price = min(
                        package.price,
                        market_price * (1 + self.config["price_flexibility"])
                    )
                    
                    # Verificar margen mínimo
                    min_price = package.cost * (1.1)  # 10% margen mínimo
                    package.price = max(new_price, min_price)
            
            return optimized
            
        except Exception as e:
            self.logger.error(f"Error optimizando competitividad: {e}")
            raise

    async def _optimize_for_balance(
        self,
        budget: Budget,
        constraints: Optional[List[OptimizationConstraint]]
    ) -> Budget:
        """Optimizar para balance precio-calidad."""
        try:
            optimized = budget.copy()
            
            # Obtener datos de calidad y mercado
            quality_data = await self.memory.get_quality_data(
                [pkg.id for pkg in optimized.packages]
            )
            
            market_data = await self.memory.get_market_data(
                [pkg.id for pkg in optimized.packages]
            )
            
            for package in optimized.packages:
                if package.id in quality_data and package.id in market_data:
                    quality_score = quality_data[package.id]["score"]
                    market_price = market_data[package.id]["avg_price"]
                    
                    # Ajustar precio según calidad
                    if quality_score > 0.8:  # Alta calidad
                        new_price = market_price * (1 + self.config["price_flexibility"])
                    elif quality_score < 0.4:  # Baja calidad
                        new_price = market_price * (1 - self.config["price_flexibility"])
                    else:  # Calidad media
                        new_price = market_price
                    
                    # Verificar margen mínimo
                    min_price = package.cost * (1.1)  # 10% margen mínimo
                    package.price = max(new_price, min_price)
            
            return optimized
            
        except Exception as e:
            self.logger.error(f"Error optimizando balance: {e}")
            raise

    def _calculate_score(
        self,
        budget: Budget,
        goal: OptimizationGoal
    ) -> float:
        """Calcular score según objetivo."""
        try:
            if goal == OptimizationGoal.MAXIMIZE_MARGIN:
                # Calcular margen promedio
                total_cost = sum(pkg.cost for pkg in budget.packages)
                total_price = sum(pkg.price for pkg in budget.packages)
                return (total_price - total_cost) / total_price
                
            elif goal == OptimizationGoal.MAXIMIZE_COMPETITIVENESS:
                # Usar inverso del precio total
                total_price = sum(pkg.price for pkg in budget.packages)
                return 1.0 / total_price
                
            else:  # BALANCE_PRICE_QUALITY
                # Combinar margen y precio
                margin_score = self._calculate_score(
                    budget,
                    OptimizationGoal.MAXIMIZE_MARGIN
                )
                competitive_score = self._calculate_score(
                    budget,
                    OptimizationGoal.MAXIMIZE_COMPETITIVENESS
                )
                return (margin_score + competitive_score) / 2
                
        except Exception as e:
            self.logger.error(f"Error calculando score: {e}")
            return 0.0

    def _calculate_stability_impact(
        self,
        budget: Budget,
        goal: OptimizationGoal
    ) -> float:
        """Calcular impacto en estabilidad."""
        try:
            impact_factors = []
            
            # Impacto por cambios de precio
            price_changes = [
                abs((pkg.price - pkg.original_price) / pkg.original_price)
                for pkg in budget.packages
                if hasattr(pkg, 'original_price')
            ]
            
            if price_changes:
                impact_factors.append(max(price_changes))
            
            # Impacto por cambios de margen
            margin_changes = [
                abs((
                    (pkg.price - pkg.cost) / pkg.price -
                    (pkg.original_price - pkg.cost) / pkg.original_price
                ))
                for pkg in budget.packages
                if hasattr(pkg, 'original_price')
            ]
            
            if margin_changes:
                impact_factors.append(max(margin_changes))
            
            # Si no hay impactos, retornar máxima estabilidad
            if not impact_factors:
                return 1.0
                
            # Retornar inverso del máximo impacto
            return 1.0 - max(impact_factors)
            
        except Exception as e:
            self.logger.error(f"Error calculando impacto: {e}")
            return 0.0

    def _validate_optimization(
        self,
        budget: Budget,
        constraints: Optional[List[OptimizationConstraint]]
    ) -> bool:
        """Validar resultado de optimización."""
        try:
            # Validar márgenes
            for package in budget.packages:
                margin = (package.price - package.cost) / package.price
                if margin < 0.1:  # Margen mínimo 10%
                    return False
            
            # Validar restricciones
            if constraints:
                for constraint in constraints:
                    if not self._validate_constraint(budget, constraint):
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando optimización: {e}")
            return False

    def _validate_constraint(
        self,
        budget: Budget,
        constraint: OptimizationConstraint
    ) -> bool:
        """Validar una restricción específica."""
        try:
            if constraint.type == "max_price":
                total_price = sum(pkg.price for pkg in budget.packages)
                return total_price <= constraint.value
                
            elif constraint.type == "min_margin":
                total_cost = sum(pkg.cost for pkg in budget.packages)
                total_price = sum(pkg.price for pkg in budget.packages)
                margin = (total_price - total_cost) / total_price
                return margin >= constraint.value
                
            elif constraint.type == "max_price_change":
                price_changes = [
                    abs((pkg.price - pkg.original_price) / pkg.original_price)
                    for pkg in budget.packages
                    if hasattr(pkg, 'original_price')
                ]
                return all(change <= constraint.value for change in price_changes)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando restricción: {e}")
            return False

# Instancia global
budget_optimizer = BudgetOptimizer()

async def get_budget_optimizer() -> BudgetOptimizer:
    """Obtener instancia del optimizador."""
    return budget_optimizer
