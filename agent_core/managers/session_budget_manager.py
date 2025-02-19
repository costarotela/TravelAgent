"""
Gestor de presupuestos en sesión.

Este módulo maneja la elaboración de presupuestos durante una sesión activa
con el cliente, asegurando estabilidad de datos durante la interacción.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
import json

from ..interfaces import StorageManager, EventEmitter, MetricsCollector, Logger, AgentComponent
from ..schemas.travel import PaqueteOLA

class SessionBudgetManager(AgentComponent):
    """
    Maneja presupuestos durante sesiones activas de venta.
    Prioriza la estabilidad de datos durante la interacción vendedor-cliente.
    """

    def __init__(
        self,
        logger: Logger,
        metrics: MetricsCollector,
        events: EventEmitter,
        storage: StorageManager
    ):
        super().__init__(logger, metrics, events)
        self.storage = storage
        self.active_sessions: Dict[str, Dict] = {}

    async def create_session(
        self,
        vendor_id: str,
        customer_id: str
    ) -> str:
        """
        Crea una nueva sesión de presupuesto.
        Captura los datos actuales para mantenerlos estables.
        """
        session_id = f"session_{vendor_id}_{customer_id}_{datetime.now().timestamp()}"
        
        self.active_sessions[session_id] = {
            'vendor_id': vendor_id,
            'customer_id': customer_id,
            'start_time': datetime.now(),
            'packages': {},
            'modifications': []
        }
        
        self.logger.info("Nueva sesión de presupuesto creada", 
                        extra={'session_id': session_id})
        
        return session_id

    async def add_package_to_session(
        self,
        session_id: str,
        package: PaqueteOLA
    ) -> Dict[str, Any]:
        """
        Agrega un paquete a la sesión, preservando sus datos actuales.
        """
        if session_id not in self.active_sessions:
            raise ValueError("Sesión no encontrada")
            
        # Crear copia inmutable del paquete para la sesión
        session_package = {
            'data': package.copy(),
            'added_at': datetime.now(),
            'modifications': []
        }
        
        self.active_sessions[session_id]['packages'][package['id']] = session_package
        
        return session_package

    async def modify_package_in_session(
        self,
        session_id: str,
        package_id: str,
        modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Modifica un paquete dentro de la sesión actual.
        Los cambios quedan registrados pero no afectan al paquete original.
        """
        if session_id not in self.active_sessions:
            raise ValueError("Sesión no encontrada")
            
        if package_id not in self.active_sessions[session_id]['packages']:
            raise ValueError("Paquete no encontrado en la sesión")
            
        session_package = self.active_sessions[session_id]['packages'][package_id]
        
        # Registrar modificación
        modification = {
            'timestamp': datetime.now(),
            'changes': modifications,
            'vendor_id': self.active_sessions[session_id]['vendor_id']
        }
        
        session_package['modifications'].append(modification)
        
        # Aplicar cambios a la copia del paquete en sesión
        for key, value in modifications.items():
            if key in session_package['data']:
                session_package['data'][key] = value
                
        return session_package

    async def finalize_session(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Finaliza la sesión y genera el presupuesto final.
        """
        if session_id not in self.active_sessions:
            raise ValueError("Sesión no encontrada")
            
        session = self.active_sessions[session_id]
        
        # Crear presupuesto final
        budget = {
            'session_id': session_id,
            'vendor_id': session['vendor_id'],
            'customer_id': session['customer_id'],
            'created_at': session['start_time'],
            'finalized_at': datetime.now(),
            'packages': session['packages'],
            'total_modifications': sum(
                len(pkg['modifications']) 
                for pkg in session['packages'].values()
            )
        }
        
        # Almacenar presupuesto
        await self.storage.save('budgets', budget)
        
        # Limpiar sesión
        del self.active_sessions[session_id]
        
        self.logger.info("Sesión de presupuesto finalizada", 
                        extra={'session_id': session_id})
        
        return budget

    async def get_session_status(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Obtiene el estado actual de una sesión.
        """
        if session_id not in self.active_sessions:
            raise ValueError("Sesión no encontrada")
            
        session = self.active_sessions[session_id]
        
        return {
            'session_id': session_id,
            'duration': (datetime.now() - session['start_time']).seconds,
            'num_packages': len(session['packages']),
            'total_modifications': sum(
                len(pkg['modifications']) 
                for pkg in session['packages'].values()
            )
        }
