"""
Servicio de integración con proveedores en tiempo real.
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Type
import os
from pathlib import Path

from ..security.credentials import CredentialManager
from .collector import ProviderCollector, APIProviderCollector, WebScraperCollector

class ProviderService:
    """Servicio central para integración con proveedores."""
    
    def __init__(self, 
                 credentials_path: Optional[str] = None,
                 encryption_key: Optional[str] = None):
        """
        Inicializa el servicio de proveedores.
        
        Args:
            credentials_path: Ruta al archivo de credenciales
            encryption_key: Clave para encriptar credenciales
        """
        self._collectors: Dict[str, ProviderCollector] = {}
        self._cache: Dict[str, Dict[str, dict]] = {}
        self._update_tasks = {}
        
        # Inicializar gestor de credenciales
        self._cred_manager = CredentialManager(encryption_key)
        if credentials_path:
            self._cred_manager.load_credentials(credentials_path)
        self._cred_manager.load_from_env()
    
    def _load_credentials(self, path: Optional[str]) -> dict:
        """Carga credenciales desde archivo o variables de entorno."""
        # Reemplazado por CredentialManager
        pass
    
    async def register_api_provider(self,
                            provider_id: str,
                            base_url: str,
                            api_key: str) -> None:
        """Registra un proveedor que expone API."""
        # Validar credenciales
        if not self._cred_manager.validate_credentials(provider_id):
            raise ValueError(f"Credenciales no válidas para {provider_id}")
        
        collector = APIProviderCollector(provider_id, base_url, api_key)
        self._collectors[provider_id] = collector
        self._cache[provider_id] = {
            "prices": {},
            "availability": {},
            "last_update": None,
            "errors": []
        }
    
    async def register_web_provider(self,
                            provider_id: str,
                            scraper_config: dict) -> None:
        """Registra un proveedor que requiere web scraping."""
        # Validar credenciales
        if not self._cred_manager.validate_credentials(provider_id):
            raise ValueError(f"Credenciales no válidas para {provider_id}")
        
        # Obtener credenciales
        creds = self._cred_manager.get_provider_credentials(provider_id)
        collector = WebScraperCollector(
            provider_id=provider_id,
            scraper_config=scraper_config,
            username=creds["username"],
            password=creds["password"]
        )
        
        # Verificar autenticación
        if not await collector.check_auth():
            await collector.close()
            raise ValueError(f"No se pudo autenticar con el proveedor {provider_id}")
        
        self._collectors[provider_id] = collector
        self._cache[provider_id] = {
            "prices": {},
            "availability": {},
            "last_update": None,
            "errors": []
        }
    
    async def start_real_time_updates(self,
                                    update_interval: int = 300) -> None:
        """
        Inicia actualizaciones periódicas de datos.
        
        Args:
            update_interval: Intervalo en segundos entre actualizaciones
        """
        for provider_id in self._collectors:
            if provider_id not in self._update_tasks:
                task = asyncio.create_task(
                    self._update_loop(provider_id, update_interval)
                )
                self._update_tasks[provider_id] = task
    
    async def _update_loop(self,
                          provider_id: str,
                          interval: int) -> None:
        """Loop de actualización para un proveedor."""
        while True:
            try:
                collector = self._collectors[provider_id]
                cache = self._cache[provider_id]
                
                # Verificar autenticación antes de actualizar
                if not await collector.check_auth():
                    raise ValueError(f"Credenciales expiradas para {provider_id}")
                
                # Actualiza precios
                prices = await collector.fetch_prices()
                cache["prices"].update(prices)
                
                # Verifica disponibilidad de ítems con precio
                availability = await collector.check_availability(
                    list(prices.keys())
                )
                cache["availability"].update(availability)
                
                cache["last_update"] = datetime.now()
                cache["errors"] = []
                
            except Exception as e:
                cache["errors"].append(str(e))
            
            await asyncio.sleep(interval)
    
    def get_current_price(self,
                         provider_id: str,
                         item_id: str) -> Optional[Decimal]:
        """Obtiene el precio actual de un ítem."""
        if cache := self._cache.get(provider_id):
            return cache["prices"].get(item_id)
        return None
    
    def is_item_available(self,
                         provider_id: str,
                         item_id: str) -> bool:
        """Verifica si un ítem está disponible."""
        if cache := self._cache.get(provider_id):
            return cache["availability"].get(item_id, False)
        return False
    
    def get_provider_status(self, provider_id: str) -> dict:
        """Obtiene el estado actual de un proveedor."""
        if not (cache := self._cache.get(provider_id)):
            return {"status": "not_found"}
            
        last_update = cache["last_update"]
        if not last_update:
            return {"status": "never_updated"}
            
        if datetime.now() - last_update > timedelta(minutes=10):
            return {
                "status": "stale",
                "last_update": last_update,
                "errors": cache["errors"]
            }
            
        return {
            "status": "active",
            "last_update": last_update,
            "items_count": len(cache["prices"]),
            "errors": cache["errors"]
        }
    
    async def force_update(self, provider_id: str) -> bool:
        """Fuerza una actualización inmediata de un proveedor."""
        if collector := self._collectors.get(provider_id):
            try:
                prices = await collector.fetch_prices()
                availability = await collector.check_availability(
                    list(prices.keys())
                )
                
                cache = self._cache[provider_id]
                cache["prices"].update(prices)
                cache["availability"].update(availability)
                cache["last_update"] = datetime.now()
                return True
                
            except Exception as e:
                if cache := self._cache.get(provider_id):
                    cache["errors"].append(str(e))
                return False
        return False
