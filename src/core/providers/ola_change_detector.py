"""Módulo para detección y procesamiento de cambios en paquetes OLA."""

from typing import Dict, List, Set
from datetime import datetime
from src.core.providers.ola_models import PaqueteOLA

class OLAChangeDetector:
    """Detector de cambios para paquetes OLA."""
    
    def __init__(self):
        """Inicializa el detector de cambios."""
        self.previous_state: Dict[str, PaqueteOLA] = {}
        self.current_state: Dict[str, PaqueteOLA] = {}
    
    def detect_changes(self, packages: List[PaqueteOLA]) -> Dict:
        """
        Detecta cambios entre el estado anterior y el actual.
        
        Args:
            packages: Lista de paquetes actuales
            
        Returns:
            Dict con listas de paquetes nuevos, actualizados y eliminados
        """
        # Guardar estado actual
        new_state = {pkg.data_hash: pkg for pkg in packages}
        
        # Si no hay estado anterior, todos son nuevos
        if not self.previous_state:
            self.previous_state = new_state.copy()
            self.current_state = new_state
            return {
                'nuevos': list(new_state.values()),
                'actualizados': [],
                'eliminados': []
            }
        
        # Obtener conjuntos de hashes
        current_hashes = set(new_state.keys())
        previous_hashes = set(self.previous_state.keys())
        
        # Detectar cambios
        new_hashes = current_hashes - previous_hashes
        deleted_hashes = previous_hashes - current_hashes
        potential_updates = current_hashes.intersection(previous_hashes)
        
        # Identificar actualizaciones reales
        updated_hashes = {
            h for h in potential_updates
            if self._has_relevant_changes(
                self.previous_state[h],
                new_state[h]
            )
        }
        
        # Construir resultado
        changes = {
            'nuevos': [new_state[h] for h in new_hashes],
            'actualizados': [new_state[h] for h in updated_hashes],
            'eliminados': [self.previous_state[h].data_hash for h in deleted_hashes]
        }
        
        # Actualizar estados
        self.current_state = new_state
        
        return changes
    
    def _has_relevant_changes(
        self,
        prev_pkg: PaqueteOLA,
        curr_pkg: PaqueteOLA
    ) -> bool:
        """
        Determina si hay cambios relevantes entre dos versiones de un paquete.
        
        Args:
            prev_pkg: Versión anterior del paquete
            curr_pkg: Versión actual del paquete
            
        Returns:
            True si hay cambios relevantes, False en caso contrario
        """
        # Lista de campos a comparar
        fields_to_compare = [
            'precio',
            'impuestos',
            'fechas',
            'incluye',
            'politicas_cancelacion',
            'vuelos',
            'cotizacion_especial',
            'restricciones',
            'assist_card'
        ]
        
        for field in fields_to_compare:
            prev_value = getattr(prev_pkg, field)
            curr_value = getattr(curr_pkg, field)
            
            # Comparación especial para fechas
            if field == 'fechas':
                prev_dates = set(d.date() for d in prev_value)
                curr_dates = set(d.date() for d in curr_value)
                if prev_dates != curr_dates:
                    return True
            
            # Comparación especial para precios e impuestos
            elif field in ['precio', 'impuestos']:
                prev_float = float(prev_value)
                curr_float = float(curr_value)
                # Tolerancia del 0.01% para cambios de precio
                tolerance = min(0.01, prev_float * 0.0001)  # Al menos 1 centavo
                if abs(prev_float - curr_float) > tolerance:
                    return True
            
            # Comparación normal para otros campos
            elif prev_value != curr_value:
                return True
        
        return False
    
    def analyze_changes(self, changes: Dict) -> Dict[str, Dict]:
        """
        Analiza los cambios detectados y genera estadísticas.
        
        Args:
            changes: Diccionario con los cambios detectados
            
        Returns:
            Dict con estadísticas de los cambios
        """
        # Analizar cambios
        stats = {
            'total_nuevos': len(changes['nuevos']),
            'total_actualizados': len(changes['actualizados']),
            'total_eliminados': len(changes['eliminados']),
            'detalles': {
                'precio': self._analyze_price_changes(changes['actualizados']),
                'disponibilidad': self._analyze_availability(changes),
                'fechas': self._analyze_date_changes(changes['actualizados'])
            }
        }
        
        # Actualizar estado anterior después del análisis
        self.previous_state = self.current_state.copy()
        
        return stats
    
    def _analyze_price_changes(self, updated_packages: List[PaqueteOLA]) -> Dict:
        """Analiza cambios en precios."""
        price_changes = []
        
        for pkg in updated_packages:
            prev_pkg = self.previous_state.get(pkg.data_hash)
            if prev_pkg and abs(float(pkg.precio) - float(prev_pkg.precio)) > 0.01:
                diff = float(pkg.precio) - float(prev_pkg.precio)
                change = {
                    'destino': pkg.destino,
                    'precio_anterior': prev_pkg.precio,
                    'precio_actual': pkg.precio,
                    'diferencia': diff,
                    'porcentaje': (diff / float(prev_pkg.precio)) * 100
                }
                price_changes.append(change)
        
        return {
            'total_cambios': len(price_changes),
            'cambios': price_changes
        }
    
    def _analyze_availability(self, changes: Dict) -> Dict:
        """Analiza cambios en disponibilidad."""
        total_packages = len(self.previous_state)
        available_packages = len(self.current_state)
        
        if total_packages == 0:
            return {
                'total_paquetes': 0,
                'paquetes_disponibles': 0,
                'porcentaje_disponible': 0
            }
        
        availability_percentage = (available_packages / total_packages) * 100
        
        return {
            'total_paquetes': total_packages,
            'paquetes_disponibles': available_packages,
            'porcentaje_disponible': availability_percentage
        }
    
    def _analyze_date_changes(self, updated_packages: List[PaqueteOLA]) -> Dict:
        """Analiza cambios en fechas disponibles."""
        date_changes = []
        
        for pkg in updated_packages:
            prev_pkg = self.previous_state.get(pkg.data_hash)
            if prev_pkg:
                prev_dates = set(d.date() for d in prev_pkg.fechas)
                curr_dates = set(d.date() for d in pkg.fechas)
                
                new_dates = curr_dates - prev_dates
                removed_dates = prev_dates - curr_dates
                
                if new_dates or removed_dates:
                    change = {
                        'destino': pkg.destino,
                        'fechas_nuevas': sorted(list(new_dates)),
                        'fechas_eliminadas': sorted(list(removed_dates))
                    }
                    date_changes.append(change)
        
        return {
            'total_cambios': len(date_changes),
            'cambios': date_changes
        }
