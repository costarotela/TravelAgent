"""
Monitor de precios de paquetes turísticos.

Este módulo se encarga de:
1. Monitorear precios de paquetes
2. Detectar cambios significativos
3. Generar alertas de oportunidades
4. Mantener histórico de precios
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from ..memory.supabase import SupabaseMemory
from .config import config
from .schemas import PriceAlert, TravelPackage, Opportunity

class PriceMonitor:
    """Monitor de precios de paquetes turísticos."""
    
    def __init__(self):
        """Inicializar monitor."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()
        self.alert_thresholds = {
            "price_drop": 0.1,  # 10% de bajada
            "price_rise": 0.1,  # 10% de subida
            "opportunity": 0.2,  # 20% por debajo del promedio
        }
    
    async def monitor_package(
        self,
        package: TravelPackage,
        track_changes: bool = True
    ) -> List[PriceAlert]:
        """
        Monitorear precio de un paquete.
        
        Args:
            package: Paquete a monitorear
            track_changes: Si se debe registrar cambios
            
        Returns:
            Lista de alertas generadas
        """
        try:
            # Obtener histórico de precios
            price_history = await self._get_price_history(package)
            
            # Registrar precio actual si es necesario
            if track_changes:
                await self._record_price(package)
            
            # Analizar cambios y generar alertas
            alerts = self._analyze_price_changes(package, price_history)
            
            # Detectar oportunidades
            opportunity = await self._detect_opportunity(package, price_history)
            if opportunity:
                alerts.append(
                    PriceAlert(
                        type="opportunity",
                        package_id=package.id,
                        message=f"Oportunidad detectada: {opportunity.description}",
                        data=opportunity.dict()
                    )
                )
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error monitoreando paquete {package.id}: {str(e)}")
            raise
    
    async def start_monitoring(
        self,
        packages: List[TravelPackage],
        interval: int = 3600  # 1 hora por defecto
    ):
        """
        Iniciar monitoreo continuo de paquetes.
        
        Args:
            packages: Lista de paquetes a monitorear
            interval: Intervalo en segundos entre chequeos
        """
        while True:
            try:
                for package in packages:
                    alerts = await self.monitor_package(package)
                    if alerts:
                        await self._process_alerts(alerts)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error en monitoreo continuo: {str(e)}")
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    async def _get_price_history(
        self,
        package: TravelPackage,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Obtener histórico de precios."""
        try:
            since = datetime.now() - timedelta(days=days)
            
            history = await self.memory.get_price_history(
                package_id=package.id,
                provider=package.provider,
                since=since
            )
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error obteniendo histórico: {str(e)}")
            return []
    
    async def _record_price(self, package: TravelPackage):
        """Registrar precio actual."""
        try:
            await self.memory.store_price(
                package_id=package.id,
                provider=package.provider,
                price=package.price,
                timestamp=datetime.now()
            )
        except Exception as e:
            self.logger.error(f"Error registrando precio: {str(e)}")
    
    def _analyze_price_changes(
        self,
        package: TravelPackage,
        price_history: List[Dict[str, Any]]
    ) -> List[PriceAlert]:
        """Analizar cambios de precio y generar alertas."""
        alerts = []
        
        if not price_history:
            return alerts
            
        # Obtener último precio registrado
        last_price = price_history[-1]["price"]
        
        # Calcular cambio porcentual
        price_change = (package.price - last_price) / last_price
        
        # Generar alertas según umbrales
        if price_change <= -self.alert_thresholds["price_drop"]:
            alerts.append(
                PriceAlert(
                    type="price_drop",
                    package_id=package.id,
                    message=f"Bajada de precio detectada: {abs(price_change)*100:.1f}%",
                    data={
                        "old_price": last_price,
                        "new_price": package.price,
                        "change_percent": price_change
                    }
                )
            )
        elif price_change >= self.alert_thresholds["price_rise"]:
            alerts.append(
                PriceAlert(
                    type="price_rise",
                    package_id=package.id,
                    message=f"Subida de precio detectada: {price_change*100:.1f}%",
                    data={
                        "old_price": last_price,
                        "new_price": package.price,
                        "change_percent": price_change
                    }
                )
            )
        
        return alerts
    
    async def _detect_opportunity(
        self,
        package: TravelPackage,
        price_history: List[Dict[str, Any]]
    ) -> Optional[Opportunity]:
        """Detectar oportunidades basadas en precio."""
        if not price_history:
            return None
            
        # Calcular precio promedio
        avg_price = sum(item["price"] for item in price_history) / len(price_history)
        
        # Calcular diferencia porcentual con promedio
        price_diff = (package.price - avg_price) / avg_price
        
        # Detectar oportunidad si precio está significativamente bajo
        if price_diff <= -self.alert_thresholds["opportunity"]:
            return Opportunity(
                type="price",
                package=package,
                savings=abs(price_diff) * avg_price,
                score=min(1.0, abs(price_diff) * 2),  # Mayor diferencia = mayor score
                valid_until=datetime.now() + timedelta(days=1),
                description=f"Precio {abs(price_diff)*100:.1f}% por debajo del promedio",
                conditions=[
                    "Sujeto a disponibilidad",
                    "Precio puede variar sin previo aviso"
                ]
            )
        
        return None
    
    async def _process_alerts(self, alerts: List[PriceAlert]):
        """Procesar alertas generadas."""
        try:
            # Almacenar alertas
            for alert in alerts:
                await self.memory.store_alert(alert.dict())
                
            # Log de alertas
            for alert in alerts:
                self.logger.info(
                    f"Alerta generada para paquete {alert.package_id}: {alert.message}"
                )
                
        except Exception as e:
            self.logger.error(f"Error procesando alertas: {str(e)}")
