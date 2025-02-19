"""
Editor de presupuestos.

Este módulo implementa:
1. Edición de presupuestos
2. Validación en tiempo real
3. Control de cambios
4. Vista previa
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from prometheus_client import Counter, Histogram

from ...schemas import (
    Budget,
    TravelPackage,
    EditOperation,
    ValidationResult
)
from ...metrics import get_metrics_collector
from ...core.budget import (
    get_budget_calculator,
    get_budget_optimizer
)
from ...core.session import get_session_manager

# Métricas
EDIT_OPERATIONS = Counter(
    'budget_edit_operations_total',
    'Number of budget edit operations',
    ['operation_type', 'status']
)

VALIDATION_TIME = Histogram(
    'budget_validation_seconds',
    'Time spent validating budget changes'
)

class BudgetEditor:
    """
    Editor de presupuestos.
    
    Responsabilidades:
    1. Editar presupuestos
    2. Validar cambios
    3. Mantener historial
    4. Generar vistas previas
    """

    def __init__(self):
        """Inicializar editor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        
        # Router FastAPI
        self.router = APIRouter(prefix="/editor")
        
        # Registrar rutas
        self._register_routes()
        
        # Configuración
        self.config = {
            "max_undo_steps": 10,
            "auto_validate": True,
            "preview_timeout": 5
        }

    def _register_routes(self) -> None:
        """Registrar rutas del editor."""
        @self.router.post("/validate")
        async def validate_changes(
            budget_id: str,
            changes: List[EditOperation]
        ) -> ValidationResult:
            """Validar cambios propuestos."""
            return await self.validate_changes(budget_id, changes)

        @self.router.post("/apply")
        async def apply_changes(
            budget_id: str,
            changes: List[EditOperation]
        ) -> Budget:
            """Aplicar cambios validados."""
            return await self.apply_changes(budget_id, changes)

        @self.router.post("/preview")
        async def generate_preview(
            budget_id: str,
            changes: List[EditOperation]
        ) -> Budget:
            """Generar vista previa."""
            return await self.generate_preview(budget_id, changes)

        @self.router.post("/undo")
        async def undo_changes(
            budget_id: str
        ) -> Budget:
            """Deshacer últimos cambios."""
            return await self.undo_changes(budget_id)

    async def validate_changes(
        self,
        budget_id: str,
        changes: List[EditOperation]
    ) -> ValidationResult:
        """
        Validar cambios propuestos.
        
        Args:
            budget_id: ID del presupuesto
            changes: Lista de cambios
            
        Returns:
            Resultado de validación
        """
        try:
            start_time = datetime.now()
            
            # Obtener presupuesto actual
            session_manager = await get_session_manager()
            session = await session_manager.get_session(budget_id)
            
            if not session or not session.budget:
                raise ValueError("Presupuesto no encontrado")
            
            # Aplicar cambios en copia
            modified_budget = session.budget.copy()
            await self._apply_operations(modified_budget, changes)
            
            # Validar resultado
            calculator = await get_budget_calculator()
            optimizer = await get_budget_optimizer()
            
            # Verificar cálculos
            calc_result = await calculator.calculate_budget(
                modified_budget.packages
            )
            
            if not calc_result.success:
                return ValidationResult(
                    valid=False,
                    errors=["Error en cálculos: " + calc_result.error]
                )
            
            # Verificar optimización
            opt_result = await optimizer.validate_budget(
                calc_result.budget
            )
            
            if not opt_result.success:
                return ValidationResult(
                    valid=False,
                    errors=["Error en optimización: " + opt_result.error]
                )
            
            # Registrar métricas
            duration = (datetime.now() - start_time).total_seconds()
            VALIDATION_TIME.observe(duration)
            
            return ValidationResult(
                valid=True,
                warnings=opt_result.warnings
            )
            
        except Exception as e:
            self.logger.error(f"Error validando cambios: {e}")
            
            EDIT_OPERATIONS.labels(
                operation_type="validate",
                status="error"
            ).inc()
            
            return ValidationResult(
                valid=False,
                errors=[str(e)]
            )

    async def apply_changes(
        self,
        budget_id: str,
        changes: List[EditOperation]
    ) -> Budget:
        """
        Aplicar cambios validados.
        
        Args:
            budget_id: ID del presupuesto
            changes: Lista de cambios
            
        Returns:
            Presupuesto actualizado
        """
        try:
            # Validar primero
            validation = await self.validate_changes(
                budget_id,
                changes
            )
            
            if not validation.valid:
                raise ValueError(
                    "Cambios inválidos: " +
                    ", ".join(validation.errors)
                )
            
            # Obtener presupuesto
            session_manager = await get_session_manager()
            session = await session_manager.get_session(budget_id)
            
            if not session or not session.budget:
                raise ValueError("Presupuesto no encontrado")
            
            # Aplicar cambios
            await self._apply_operations(session.budget, changes)
            
            # Actualizar sesión
            success = await session_manager.update_session(
                budget_id,
                session.budget,
                "Applied changes from editor"
            )
            
            if not success:
                raise ValueError("Error actualizando sesión")
            
            # Registrar operación
            EDIT_OPERATIONS.labels(
                operation_type="apply",
                status="success"
            ).inc()
            
            return session.budget
            
        except Exception as e:
            self.logger.error(f"Error aplicando cambios: {e}")
            
            EDIT_OPERATIONS.labels(
                operation_type="apply",
                status="error"
            ).inc()
            
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

    async def generate_preview(
        self,
        budget_id: str,
        changes: List[EditOperation]
    ) -> Budget:
        """
        Generar vista previa.
        
        Args:
            budget_id: ID del presupuesto
            changes: Lista de cambios
            
        Returns:
            Presupuesto con cambios
        """
        try:
            # Obtener presupuesto
            session_manager = await get_session_manager()
            session = await session_manager.get_session(budget_id)
            
            if not session or not session.budget:
                raise ValueError("Presupuesto no encontrado")
            
            # Crear copia para preview
            preview_budget = session.budget.copy()
            
            # Aplicar cambios
            await self._apply_operations(preview_budget, changes)
            
            # Calcular resultados
            calculator = await get_budget_calculator()
            result = await calculator.calculate_budget(
                preview_budget.packages
            )
            
            if not result.success:
                raise ValueError("Error calculando preview")
            
            # Registrar operación
            EDIT_OPERATIONS.labels(
                operation_type="preview",
                status="success"
            ).inc()
            
            return result.budget
            
        except Exception as e:
            self.logger.error(f"Error generando preview: {e}")
            
            EDIT_OPERATIONS.labels(
                operation_type="preview",
                status="error"
            ).inc()
            
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

    async def undo_changes(
        self,
        budget_id: str
    ) -> Budget:
        """
        Deshacer últimos cambios.
        
        Args:
            budget_id: ID del presupuesto
            
        Returns:
            Presupuesto anterior
        """
        try:
            # Obtener sesión
            session_manager = await get_session_manager()
            session = await session_manager.get_session(budget_id)
            
            if not session:
                raise ValueError("Sesión no encontrada")
            
            # Obtener snapshots
            snapshots = await session_manager.get_snapshots(budget_id)
            
            if not snapshots:
                raise ValueError("No hay cambios para deshacer")
            
            # Restaurar último snapshot
            success = await session_manager.restore_snapshot(
                budget_id,
                snapshots[-1].id
            )
            
            if not success:
                raise ValueError("Error restaurando snapshot")
            
            # Registrar operación
            EDIT_OPERATIONS.labels(
                operation_type="undo",
                status="success"
            ).inc()
            
            return session.budget
            
        except Exception as e:
            self.logger.error(f"Error deshaciendo cambios: {e}")
            
            EDIT_OPERATIONS.labels(
                operation_type="undo",
                status="error"
            ).inc()
            
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

    async def _apply_operations(
        self,
        budget: Budget,
        operations: List[EditOperation]
    ) -> None:
        """Aplicar operaciones de edición."""
        try:
            for operation in operations:
                if operation.type == "update_package":
                    # Actualizar paquete
                    package = next(
                        (p for p in budget.packages
                         if p.id == operation.target_id),
                        None
                    )
                    
                    if not package:
                        raise ValueError(
                            f"Paquete {operation.target_id} no encontrado"
                        )
                    
                    for field, value in operation.changes.items():
                        setattr(package, field, value)
                
                elif operation.type == "add_package":
                    # Agregar paquete
                    package = TravelPackage(**operation.changes)
                    budget.packages.append(package)
                
                elif operation.type == "remove_package":
                    # Eliminar paquete
                    budget.packages = [
                        p for p in budget.packages
                        if p.id != operation.target_id
                    ]
                
                elif operation.type == "update_metadata":
                    # Actualizar metadata
                    for field, value in operation.changes.items():
                        setattr(budget, field, value)
            
        except Exception as e:
            self.logger.error(f"Error aplicando operaciones: {e}")
            raise

# Instancia global
budget_editor = BudgetEditor()

def get_budget_editor() -> BudgetEditor:
    """Obtener instancia del editor."""
    return budget_editor
