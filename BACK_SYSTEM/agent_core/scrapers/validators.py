"""
Validadores para datos extraídos del scraper.

Este módulo implementa validaciones para asegurar la integridad y formato
de los datos extraídos por los scrapers.
"""

from typing import Dict, List, Any
from decimal import Decimal
from datetime import datetime

class ValidationError(Exception):
    """Error de validación de datos."""
    pass

class DataValidator:
    """Validador de datos extraídos."""

    def validate_package(self, data: Dict[str, Any]) -> None:
        """Valida los datos completos de un paquete."""
        required_fields = [
            'destino',
            'aerolinea',
            'duracion',
            'precio',
            'impuestos',
            'incluye',
            'fechas'
        ]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Campo requerido faltante: {field}")
        
        # Validar tipos de datos
        if not isinstance(data['destino'], str) or not data['destino'].strip():
            raise ValidationError("Destino inválido")
            
        if not isinstance(data['aerolinea'], str) or not data['aerolinea'].strip():
            raise ValidationError("Aerolínea inválida")
            
        if not isinstance(data['duracion'], str) or not data['duracion'].strip():
            raise ValidationError("Duración inválida")
            
        if not isinstance(data['precio'], Decimal) or data['precio'] <= 0:
            raise ValidationError("Precio inválido")
            
        if not isinstance(data['impuestos'], Decimal) or data['impuestos'] < 0:
            raise ValidationError("Impuestos inválidos")
            
        if not isinstance(data['incluye'], list):
            raise ValidationError("Campo 'incluye' debe ser una lista")
            
        if not isinstance(data['fechas'], list):
            raise ValidationError("Campo 'fechas' debe ser una lista")
            
        # Validar fechas
        for fecha in data['fechas']:
            try:
                datetime.strptime(fecha, '%Y-%m-%d')
            except ValueError:
                raise ValidationError(f"Fecha inválida: {fecha}")

    def validate_flight(self, data: Dict[str, Any]) -> None:
        """Valida los datos de un vuelo."""
        required_fields = ['salida', 'llegada', 'duracion']
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Campo de vuelo requerido faltante: {field}")
        
        # Validar tipos de datos
        if not isinstance(data['salida'], str) or not data['salida'].strip():
            raise ValidationError("Salida inválida")
            
        if not isinstance(data['llegada'], str) or not data['llegada'].strip():
            raise ValidationError("Llegada inválida")
            
        if not isinstance(data['duracion'], str) or not data['duracion'].strip():
            raise ValidationError("Duración de vuelo inválida")
            
        # Validar escalas si existen
        if 'escalas' in data:
            if not isinstance(data['escalas'], list):
                raise ValidationError("Escalas debe ser una lista")
                
            for escala in data['escalas']:
                if not isinstance(escala, dict):
                    raise ValidationError("Escala debe ser un diccionario")
                    
                if 'ubicacion' not in escala or 'tiempo_espera' not in escala:
                    raise ValidationError("Escala debe tener ubicación y tiempo de espera")

    def validate_cancellation_policies(self, policies: List[Dict]) -> None:
        """Valida las políticas de cancelación."""
        if not isinstance(policies, list):
            raise ValidationError("Políticas debe ser una lista")
            
        for policy in policies:
            if not isinstance(policy, dict):
                raise ValidationError("Política debe ser un diccionario")
                
            if 'periodo' not in policy or 'penalidad' not in policy:
                raise ValidationError("Política debe tener periodo y penalidad")
                
            if not isinstance(policy['periodo'], str) or not policy['periodo'].strip():
                raise ValidationError("Periodo de política inválido")
                
            if not isinstance(policy['penalidad'], str) or not policy['penalidad'].strip():
                raise ValidationError("Penalidad de política inválida")

    def validate_assist_card(self, data: Dict[str, Any]) -> None:
        """Valida los datos de Assist Card."""
        required_fields = [
            'cobertura',
            'validez',
            'territorialidad',
            'limitaciones',
            'gastos_reserva'
        ]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Campo de Assist Card requerido faltante: {field}")
        
        # Validar tipos de datos
        if not isinstance(data['cobertura'], Decimal) or data['cobertura'] <= 0:
            raise ValidationError("Cobertura inválida")
            
        if not isinstance(data['validez'], str) or not data['validez'].strip():
            raise ValidationError("Validez inválida")
            
        if not isinstance(data['territorialidad'], str) or not data['territorialidad'].strip():
            raise ValidationError("Territorialidad inválida")
            
        if not isinstance(data['limitaciones'], str) or not data['limitaciones'].strip():
            raise ValidationError("Limitaciones inválidas")
            
        if not isinstance(data['gastos_reserva'], Decimal) or data['gastos_reserva'] < 0:
            raise ValidationError("Gastos de reserva inválidos")

    def validate_special_taxes(self, taxes: List[Dict]) -> None:
        """Valida los impuestos especiales."""
        if not isinstance(taxes, list):
            raise ValidationError("Impuestos debe ser una lista")
            
        for tax in taxes:
            if not isinstance(tax, dict):
                raise ValidationError("Impuesto debe ser un diccionario")
                
            if 'nombre' not in tax or 'monto' not in tax or 'detalle' not in tax:
                raise ValidationError("Impuesto debe tener nombre, monto y detalle")
                
            if not isinstance(tax['nombre'], str) or not tax['nombre'].strip():
                raise ValidationError("Nombre de impuesto inválido")
                
            if not isinstance(tax['monto'], Decimal) or tax['monto'] < 0:
                raise ValidationError("Monto de impuesto inválido")
                
            if not isinstance(tax['detalle'], str):
                raise ValidationError("Detalle de impuesto inválido")

    def validate_search_criteria(self, criteria: Dict[str, Any]) -> None:
        """Valida los criterios de búsqueda."""
        if not isinstance(criteria, dict):
            raise ValidationError("Criterios debe ser un diccionario")
            
        # Validar campos requeridos
        required_fields = ['destino']
        for field in required_fields:
            if field not in criteria:
                raise ValidationError(f"Criterio requerido faltante: {field}")
        
        # Validar tipos de datos
        if not isinstance(criteria['destino'], str) or not criteria['destino'].strip():
            raise ValidationError("Destino inválido")
            
        # Validar fechas si están presentes
        if 'fechas' in criteria:
            if not isinstance(criteria['fechas'], list):
                raise ValidationError("Fechas debe ser una lista")
                
            for fecha in criteria['fechas']:
                try:
                    datetime.strptime(fecha, '%Y-%m-%d')
                except ValueError:
                    raise ValidationError(f"Fecha inválida: {fecha}")
