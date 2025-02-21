"""Módulo de gestión de memoria."""

from typing import Dict, Any


class MemoryManager:
    """Gestor de memoria para el sistema."""
    
    def __init__(self):
        """Inicializa el gestor de memoria."""
        self._memory = {}
    
    def get(self, key: str) -> Any:
        """Obtiene un valor de memoria."""
        return self._memory.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Establece un valor en memoria."""
        self._memory[key] = value
    
    def clear(self) -> None:
        """Limpia la memoria."""
        self._memory.clear()


# Instancia global
_memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """Obtiene la instancia global del gestor de memoria."""
    return _memory_manager
