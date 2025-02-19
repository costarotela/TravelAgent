"""Cache utilities."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class SimpleCache:
    """Cache simple para el sistema."""
    
    def __init__(self):
        """Inicializar cache."""
        self.cache: Dict[str, Any] = {}
        self.expiry: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache."""
        if key not in self.cache:
            return None
            
        if key in self.expiry and datetime.now() > self.expiry[key]:
            del self.cache[key]
            del self.expiry[key]
            return None
            
        return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Establecer valor en cache."""
        self.cache[key] = value
        if ttl:
            self.expiry[key] = datetime.now() + timedelta(seconds=ttl)
    
    def delete(self, key: str):
        """Eliminar valor del cache."""
        if key in self.cache:
            del self.cache[key]
        if key in self.expiry:
            del self.expiry[key]
    
    def clear(self):
        """Limpiar todo el cache."""
        self.cache.clear()
        self.expiry.clear()
        
# Instancia global del cache
cache = SimpleCache()
