"""
Módulo de gestión de sesiones para la interfaz de vendedor.

Este paquete proporciona las herramientas necesarias para mantener
el estado de las sesiones de vendedor durante la elaboración de presupuestos.
"""

from .manager import SessionManager
from .models import SessionState, VendorSession

__all__ = ['SessionManager', 'SessionState', 'VendorSession']
