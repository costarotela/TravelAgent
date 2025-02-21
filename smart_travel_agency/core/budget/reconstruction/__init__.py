"""
Sistema de reconstrucción de presupuestos.

Este módulo provee una capa de alto nivel sobre el reconstructor core,
agregando funcionalidades como análisis de impacto, manejo de sesiones,
y estrategias avanzadas de reconstrucción.
"""

from ..reconstructor import (
    BudgetReconstructor,
    get_budget_reconstructor,
    ReconstructionStrategy,
)

from .manager import (
    BudgetReconstructionManager,
    get_reconstruction_manager,
    ReconstructionResult,
)

from .session_manager import (
    SessionManager,
    get_session_manager,
    SessionState,
)

from .analysis import (
    ImpactAnalyzer,
    AnalysisResult,
)

__all__ = [
    # Core components
    'BudgetReconstructor',
    'get_budget_reconstructor',
    'ReconstructionStrategy',
    
    # High-level management
    'BudgetReconstructionManager',
    'get_reconstruction_manager',
    'ReconstructionResult',
    
    # Session handling
    'SessionManager',
    'get_session_manager',
    'SessionState',
    
    # Analysis
    'ImpactAnalyzer',
    'AnalysisResult',
]
