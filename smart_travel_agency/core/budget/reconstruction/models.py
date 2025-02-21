"""
Modelos para el sistema de reconstrucción.

Define los modelos de datos necesarios para el proceso
de reconstrucción de presupuestos.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class ReconstructionResult:
    """
    Resultado de una operación de reconstrucción.
    
    Attributes:
        budget_id: ID del presupuesto reconstruido
        success: Si la reconstrucción fue exitosa
        changes_applied: Cambios aplicados durante la reconstrucción
        strategy_used: Estrategia utilizada
        error_message: Mensaje de error si hubo fallo
    """
    
    budget_id: str
    success: bool
    changes_applied: Dict[str, Any]
    strategy_used: str
    error_message: Optional[str] = None
    timestamp: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "budget_id": self.budget_id,
            "success": self.success,
            "changes_applied": self.changes_applied,
            "strategy_used": self.strategy_used,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message
        }
