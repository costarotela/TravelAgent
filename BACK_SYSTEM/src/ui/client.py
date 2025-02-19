"""Cliente para la API de Travel Agent."""

import httpx
from typing import Optional, Dict, Any
from datetime import datetime

class TravelAgentClient:
    """Cliente para interactuar con la API de Travel Agent."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        """Inicializar cliente."""
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None
        self._client = httpx.AsyncClient(base_url=self.base_url)

    async def create_session(self, vendor_id: str, customer_id: str) -> str:
        """Crear una nueva sesión."""
        response = await self._client.post(
            "/api/v1/sessions/create",
            params={"vendor_id": vendor_id, "customer_id": customer_id}
        )
        response.raise_for_status()
        data = response.json()
        self.session_id = data["session_id"]
        return self.session_id

    async def add_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        """Agregar un paquete a la sesión actual."""
        if not self.session_id:
            raise ValueError("No hay una sesión activa")
        
        response = await self._client.post(
            f"/api/v1/sessions/{self.session_id}/packages",
            json=package
        )
        response.raise_for_status()
        return response.json()

    async def get_budget(self) -> Dict[str, Any]:
        """Obtener el presupuesto actual."""
        if not self.session_id:
            raise ValueError("No hay una sesión activa")
        
        response = await self._client.get(
            f"/api/v1/sessions/{self.session_id}/budget"
        )
        response.raise_for_status()
        return response.json()

    async def add_modification(self, modification: Dict[str, Any]) -> Dict[str, Any]:
        """Agregar una modificación al presupuesto."""
        if not self.session_id:
            raise ValueError("No hay una sesión activa")
        
        response = await self._client.post(
            f"/api/v1/sessions/{self.session_id}/modifications",
            json=modification
        )
        response.raise_for_status()
        return response.json()

    async def close_session(self) -> Dict[str, Any]:
        """Cerrar la sesión actual."""
        if not self.session_id:
            raise ValueError("No hay una sesión activa")
        
        response = await self._client.post(
            f"/api/v1/sessions/{self.session_id}/close"
        )
        response.raise_for_status()
        result = response.json()
        self.session_id = None
        return result

    async def __aenter__(self):
        """Soporte para context manager async."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup al salir del context manager."""
        await self._client.aclose()
