"""
Seguimiento de cambios en sesiones.

Este módulo implementa:
1. Registro de cambios
2. Historial de modificaciones
3. Auditoría de sesiones
4. Análisis de patrones
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from prometheus_client import Counter, Histogram

from ..schemas import (
    SessionState,
    Budget,
    TravelPackage,
    ChangeRecord,
    ChangePattern
)
from ..metrics import get_metrics_collector
from .state_manager import get_session_manager

# Métricas
CHANGE_OPERATIONS = Counter(
    'change_operations_total',
    'Number of change operations',
    ['change_type']
)

CHANGE_LATENCY = Histogram(
    'change_operation_latency_seconds',
    'Latency of change operations',
    ['operation_type']
)

class ChangeTracker:
    """
    Seguimiento de cambios.
    
    Responsabilidades:
    1. Registrar cambios
    2. Mantener historial
    3. Analizar patrones
    """

    def __init__(self):
        """Inicializar tracker."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        
        # Almacenamiento de cambios
        self._changes: Dict[str, List[ChangeRecord]] = {}
        self._patterns: Dict[str, List[ChangePattern]] = {}
        
        # Configuración
        self.config = {
            "max_changes": 100,     # Máximo de cambios por sesión
            "pattern_threshold": 3,  # Mínimo de ocurrencias para patrón
            "analysis_window": 10    # Ventana de análisis de patrones
        }

    async def record_change(
        self,
        session_id: str,
        change_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ) -> ChangeRecord:
        """
        Registrar un cambio.
        
        Args:
            session_id: ID de la sesión
            change_type: Tipo de cambio
            description: Descripción del cambio
            details: Detalles adicionales
            
        Returns:
            Registro del cambio
        """
        try:
            # Crear registro
            record = ChangeRecord(
                id=len(self._changes.get(session_id, [])) + 1,
                session_id=session_id,
                timestamp=datetime.now(),
                change_type=change_type,
                description=description,
                details=details or {}
            )
            
            # Almacenar cambio
            if session_id not in self._changes:
                self._changes[session_id] = []
            
            changes = self._changes[session_id]
            
            # Mantener límite de cambios
            if len(changes) >= self.config["max_changes"]:
                changes.pop(0)
            
            changes.append(record)
            
            # Registrar métrica
            CHANGE_OPERATIONS.labels(
                change_type=change_type
            ).inc()
            
            # Analizar patrones
            await self._analyze_patterns(session_id)
            
            return record
            
        except Exception as e:
            self.logger.error(f"Error registrando cambio: {e}")
            raise

    async def get_changes(
        self,
        session_id: str,
        change_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ChangeRecord]:
        """
        Obtener cambios filtrados.
        
        Args:
            session_id: ID de la sesión
            change_type: Tipo de cambio opcional
            start_time: Tiempo inicial opcional
            end_time: Tiempo final opcional
            
        Returns:
            Lista de cambios filtrados
        """
        try:
            changes = self._changes.get(session_id, [])
            
            # Aplicar filtros
            if change_type:
                changes = [c for c in changes if c.change_type == change_type]
            
            if start_time:
                changes = [c for c in changes if c.timestamp >= start_time]
            
            if end_time:
                changes = [c for c in changes if c.timestamp <= end_time]
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Error obteniendo cambios: {e}")
            return []

    async def get_patterns(
        self,
        session_id: str
    ) -> List[ChangePattern]:
        """
        Obtener patrones detectados.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Lista de patrones
        """
        try:
            return self._patterns.get(session_id, [])
            
        except Exception as e:
            self.logger.error(f"Error obteniendo patrones: {e}")
            return []

    async def analyze_session(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Analizar sesión completa.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Análisis de la sesión
        """
        try:
            changes = await self.get_changes(session_id)
            patterns = await self.get_patterns(session_id)
            
            # Calcular estadísticas
            change_types = {}
            for change in changes:
                if change.change_type not in change_types:
                    change_types[change.change_type] = 0
                change_types[change.change_type] += 1
            
            # Calcular duración
            if changes:
                duration = (
                    changes[-1].timestamp -
                    changes[0].timestamp
                ).total_seconds()
            else:
                duration = 0
            
            return {
                "total_changes": len(changes),
                "change_types": change_types,
                "patterns_detected": len(patterns),
                "duration_seconds": duration,
                "changes_per_minute": (
                    len(changes) / (duration / 60)
                    if duration > 0 else 0
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error analizando sesión: {e}")
            return {}

    async def _analyze_patterns(
        self,
        session_id: str
    ) -> None:
        """Analizar patrones en cambios recientes."""
        try:
            changes = self._changes.get(session_id, [])
            
            if len(changes) < self.config["pattern_threshold"]:
                return
            
            # Analizar ventana reciente
            window = changes[-self.config["analysis_window"]:]
            
            # Detectar secuencias repetidas
            sequences = {}
            for i in range(len(window) - 1):
                for j in range(i + 2, len(window) + 1):
                    sequence = tuple(
                        c.change_type for c in window[i:j]
                    )
                    
                    if sequence not in sequences:
                        sequences[sequence] = 0
                    sequences[sequence] += 1
            
            # Filtrar patrones significativos
            patterns = []
            for sequence, count in sequences.items():
                if count >= self.config["pattern_threshold"]:
                    pattern = ChangePattern(
                        sequence=list(sequence),
                        occurrences=count,
                        last_seen=changes[-1].timestamp
                    )
                    patterns.append(pattern)
            
            # Actualizar patrones
            self._patterns[session_id] = patterns
            
        except Exception as e:
            self.logger.error(f"Error analizando patrones: {e}")

# Instancia global
change_tracker = ChangeTracker()

async def get_change_tracker() -> ChangeTracker:
    """Obtener instancia del tracker."""
    return change_tracker
