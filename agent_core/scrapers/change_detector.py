"""
Detector simple de cambios en paquetes turísticos.
Versión mínima viable que se enfoca solo en cambios críticos.
"""

from typing import Dict, Optional
from decimal import Decimal
from ..schemas.travel import PaqueteOLA

class ChangeDetector:
    """
    Detector simple de cambios críticos en paquetes.
    Se enfoca solo en cambios que afectan directamente a los presupuestos.
    """

    def detect_changes(self, old_data: PaqueteOLA, new_data: PaqueteOLA) -> Dict:
        """
        Detecta cambios críticos entre dos versiones de un paquete.
        Solo detecta cambios que afectan directamente a los presupuestos.
        """
        changes = {}

        # Cambio en precio (crítico para presupuestos)
        if old_data.precio != new_data.precio:
            changes['precio'] = {
                'anterior': old_data.precio,
                'actual': new_data.precio,
                'diferencia': new_data.precio - old_data.precio
            }

        # Cambio en disponibilidad (crítico para ventas)
        old_fechas = set(old_data.fechas)
        new_fechas = set(new_data.fechas)
        
        fechas_removidas = old_fechas - new_fechas
        fechas_agregadas = new_fechas - old_fechas
        
        if fechas_removidas or fechas_agregadas:
            changes['disponibilidad'] = {
                'fechas_removidas': list(fechas_removidas),
                'fechas_agregadas': list(fechas_agregadas)
            }

        # Cambio en impuestos (afecta precio final)
        if old_data.impuestos != new_data.impuestos:
            changes['impuestos'] = {
                'anterior': old_data.impuestos,
                'actual': new_data.impuestos,
                'diferencia': new_data.impuestos - old_data.impuestos
            }

        return changes

    def is_significant_change(self, changes: Dict) -> bool:
        """
        Determina si los cambios detectados son significativos.
        Un cambio es significativo si afecta precio o disponibilidad.
        """
        if not changes:
            return False

        # Cambio significativo en precio (>5%)
        if 'precio' in changes:
            precio_anterior = changes['precio']['anterior']
            diferencia_porcentual = abs(changes['precio']['diferencia'] / precio_anterior * 100)
            if diferencia_porcentual > 5:
                return True

        # Cualquier cambio en disponibilidad es significativo
        if 'disponibilidad' in changes:
            return True

        # Cambio significativo en impuestos (>5%)
        if 'impuestos' in changes:
            impuestos_anterior = changes['impuestos']['anterior']
            if impuestos_anterior > 0:  # Evitar división por cero
                diferencia_porcentual = abs(changes['impuestos']['diferencia'] / impuestos_anterior * 100)
                if diferencia_porcentual > 5:
                    return True

        return False
