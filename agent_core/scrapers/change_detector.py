"""
Detector de cambios en paquetes turísticos.

Este módulo implementa la detección y validación de cambios en paquetes turísticos.
Es un componente IMPRESCINDIBLE que:
1. Detecta cambios que afectan a los presupuestos
2. Valida la integridad de los cambios detectados
3. Prioriza cambios según su impacto
4. Registra métricas de cambios
"""

from typing import Dict, Optional, List, Any
from decimal import Decimal
from datetime import datetime
import json

from prometheus_client import Counter, Histogram

from .validators import DataValidator, ValidationError
from .error_handler import ErrorHandler
from ..schemas.travel import PaqueteOLA

# Métricas Prometheus
CHANGES_DETECTED = Counter(
    'package_changes_detected_total',
    'Total number of package changes detected',
    ['change_type']
)

CHANGE_MAGNITUDE = Histogram(
    'package_change_magnitude',
    'Magnitude of changes detected in packages',
    ['change_type'],
    buckets=[1, 2, 5, 10, 20, 50, 100]
)

class ChangeDetector:
    """
    Detector de cambios en paquetes turísticos con validación integrada.
    """

    def __init__(self):
        """Inicializa el detector con validador y manejador de errores."""
        self.validator = DataValidator()
        self.error_handler = ErrorHandler("change_detector")
        self.significant_change_threshold = 5  # Porcentaje

    def detect_changes(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict:
        """
        Detecta y valida cambios entre dos versiones de un paquete.
        
        Args:
            old_data: Datos anteriores del paquete
            new_data: Datos nuevos del paquete
            
        Returns:
            Dict con los cambios detectados y validados
            
        Raises:
            ValidationError: Si los datos no son válidos
        """
        try:
            # Validar datos de entrada
            self.validator.validate_package(old_data)
            self.validator.validate_package(new_data)
            
            changes = {}
            
            # Detectar cambios en precio
            if old_data['precio'] != new_data['precio']:
                diferencia = new_data['precio'] - old_data['precio']
                diferencia_porcentual = abs(diferencia / old_data['precio'] * 100)
                
                changes['precio'] = {
                    'anterior': old_data['precio'],
                    'actual': new_data['precio'],
                    'diferencia': diferencia,
                    'diferencia_porcentual': diferencia_porcentual
                }
                
                CHANGES_DETECTED.labels(change_type='precio').inc()
                CHANGE_MAGNITUDE.labels(change_type='precio').observe(float(diferencia_porcentual))

            # Detectar cambios en disponibilidad
            old_fechas = set(old_data['fechas'])
            new_fechas = set(new_data['fechas'])
            
            fechas_removidas = old_fechas - new_fechas
            fechas_agregadas = new_fechas - old_fechas
            
            if fechas_removidas or fechas_agregadas:
                changes['disponibilidad'] = {
                    'fechas_removidas': sorted(list(fechas_removidas)),
                    'fechas_agregadas': sorted(list(fechas_agregadas))
                }
                
                CHANGES_DETECTED.labels(change_type='disponibilidad').inc()

            # Detectar cambios en impuestos
            if old_data['impuestos'] != new_data['impuestos']:
                diferencia = new_data['impuestos'] - old_data['impuestos']
                diferencia_porcentual = abs(diferencia / old_data['impuestos'] * 100) if old_data['impuestos'] > 0 else 100
                
                changes['impuestos'] = {
                    'anterior': old_data['impuestos'],
                    'actual': new_data['impuestos'],
                    'diferencia': diferencia,
                    'diferencia_porcentual': diferencia_porcentual
                }
                
                CHANGES_DETECTED.labels(change_type='impuestos').inc()
                CHANGE_MAGNITUDE.labels(change_type='impuestos').observe(float(diferencia_porcentual))

            # Detectar cambios en políticas de cancelación
            if self._detect_policy_changes(old_data.get('politicas', []), new_data.get('politicas', [])):
                changes['politicas'] = {
                    'anterior': old_data.get('politicas', []),
                    'actual': new_data.get('politicas', [])
                }
                CHANGES_DETECTED.labels(change_type='politicas').inc()

            # Detectar cambios en Assist Card
            if 'assist_card' in old_data and 'assist_card' in new_data:
                assist_changes = self._detect_assist_card_changes(old_data['assist_card'], new_data['assist_card'])
                self.error_handler.log_operation(
                    "assist_card_debug",
                    old_assist=json.dumps(old_data['assist_card'], default=str),
                    new_assist=json.dumps(new_data['assist_card'], default=str),
                    changes=json.dumps(assist_changes, default=str) if assist_changes else "None"
                )
                if assist_changes:
                    changes['assist_card'] = assist_changes
                    CHANGES_DETECTED.labels(change_type='assist_card').inc()

            # Registrar cambios detectados
            if changes:
                self.error_handler.log_operation(
                    "changes_detected",
                    changes=json.dumps(changes, default=str)
                )

            return changes

        except ValidationError as e:
            self.error_handler.log_operation(
                "validation_error",
                error=str(e),
                old_data=json.dumps(old_data, default=str),
                new_data=json.dumps(new_data, default=str)
            )
            raise

    def is_significant_change(self, changes: Dict) -> bool:
        """
        Determina si los cambios detectados son significativos.
        
        Args:
            changes: Diccionario con los cambios detectados
            
        Returns:
            True si los cambios son significativos, False en caso contrario
        """
        if not changes:
            return False

        # Cambio significativo en precio
        if 'precio' in changes:
            if changes['precio']['diferencia_porcentual'] > self.significant_change_threshold:
                return True

        # Cualquier cambio en disponibilidad es significativo
        if 'disponibilidad' in changes:
            return True

        # Cambio significativo en impuestos
        if 'impuestos' in changes:
            if changes['impuestos']['diferencia_porcentual'] > self.significant_change_threshold:
                return True

        # Cambios en políticas siempre son significativos
        if 'politicas' in changes:
            return True

        # Cambios significativos en Assist Card
        if 'assist_card' in changes:
            if 'cobertura' in changes['assist_card']:
                if changes['assist_card']['cobertura']['diferencia_porcentual'] > self.significant_change_threshold:
                    return True
            # Otros cambios en assist_card son significativos
            if any(field in changes['assist_card'] for field in ['validez', 'territorialidad', 'limitaciones']):
                return True

        return False

    def _detect_policy_changes(self, old_policies: List[Dict], new_policies: List[Dict]) -> bool:
        """Detecta cambios en políticas de cancelación."""
        try:
            # Validar políticas
            self.validator.validate_cancellation_policies(old_policies)
            self.validator.validate_cancellation_policies(new_policies)
            
            # Convertir a conjuntos para comparación
            old_set = {json.dumps(policy, sort_keys=True) for policy in old_policies}
            new_set = {json.dumps(policy, sort_keys=True) for policy in new_policies}
            
            return old_set != new_set
            
        except ValidationError:
            return True  # Si hay error de validación, considerar como cambio

    def _detect_assist_card_changes(self, old_assist: Dict, new_assist: Dict) -> Optional[Dict]:
        """Detecta cambios en Assist Card."""
        try:
            # Validar datos de Assist Card
            self.validator.validate_assist_card(old_assist)
            self.validator.validate_assist_card(new_assist)
            
            changes = {}
            
            # Detectar cambios en cobertura
            if old_assist['cobertura'] != new_assist['cobertura']:
                diferencia = new_assist['cobertura'] - old_assist['cobertura']
                diferencia_porcentual = abs(diferencia / old_assist['cobertura'] * 100)
                
                changes['cobertura'] = {
                    'anterior': old_assist['cobertura'],
                    'actual': new_assist['cobertura'],
                    'diferencia': diferencia,
                    'diferencia_porcentual': diferencia_porcentual
                }
                
                CHANGE_MAGNITUDE.labels(change_type='assist_card').observe(float(diferencia_porcentual))
                
                self.error_handler.log_operation(
                    "assist_card_cobertura_debug",
                    old_cobertura=str(old_assist['cobertura']),
                    new_cobertura=str(new_assist['cobertura']),
                    diferencia=str(diferencia),
                    diferencia_porcentual=str(diferencia_porcentual)
                )
            
            # Detectar otros cambios
            for field in ['validez', 'territorialidad', 'limitaciones']:
                if old_assist.get(field) != new_assist.get(field):
                    changes[field] = {
                        'anterior': old_assist.get(field),
                        'actual': new_assist.get(field)
                    }
            
            return changes if changes else None
            
        except ValidationError as e:
            self.error_handler.log_operation(
                "assist_card_validation_error",
                error=str(e),
                old_assist=json.dumps(old_assist, default=str),
                new_assist=json.dumps(new_assist, default=str)
            )
            return None
        except Exception as e:
            self.error_handler.log_operation(
                "assist_card_unexpected_error",
                error=str(e),
                old_assist=json.dumps(old_assist, default=str),
                new_assist=json.dumps(new_assist, default=str)
            )
            return None
