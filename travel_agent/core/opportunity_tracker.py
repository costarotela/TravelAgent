"""
Tracker de oportunidades de viaje.

Este módulo se encarga de:
1. Rastrear oportunidades en tiempo real
2. Analizar tendencias de mercado
3. Detectar ofertas especiales
4. Priorizar oportunidades según criterios
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from .schemas import Opportunity, TravelPackage, SearchCriteria
from .package_analyzer import PackageAnalyzer
from .price_monitor import PriceMonitor
from ..memory.supabase import SupabaseMemory


class OpportunityTracker:
    """Tracker de oportunidades de viaje."""
    
    def __init__(self):
        """Inicializar tracker."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()
        self.analyzer = PackageAnalyzer()
        self.price_monitor = PriceMonitor()
        
        # Configuración de umbrales
        self.thresholds = {
            "min_score": 0.7,          # Puntuación mínima para considerar
            "min_savings": 100,         # Ahorro mínimo en USD
            "max_opportunities": 10,    # Máximo de oportunidades activas
            "expiry_hours": 24         # Horas hasta expiración
        }
    
    async def track_opportunities(
        self,
        packages: List[TravelPackage],
        criteria: Optional[SearchCriteria] = None
    ) -> List[Opportunity]:
        """
        Rastrear oportunidades en paquetes.
        
        Args:
            packages: Lista de paquetes a analizar
            criteria: Criterios específicos de búsqueda
            
        Returns:
            Lista de oportunidades detectadas
        """
        try:
            opportunities = []
            
            for package in packages:
                # Analizar paquete
                analysis = await self.analyzer.analyze_package(
                    package=package,
                    criteria=criteria.dict() if criteria else {}
                )
                
                # Verificar alertas de precio
                price_alerts = await self.price_monitor.monitor_package(
                    package=package,
                    track_changes=True
                )
                
                # Detectar oportunidad si cumple criterios
                if self._is_opportunity(analysis, price_alerts):
                    opportunity = await self._create_opportunity(
                        package=package,
                        analysis=analysis,
                        alerts=price_alerts
                    )
                    opportunities.append(opportunity)
            
            # Priorizar y filtrar oportunidades
            opportunities = self._prioritize_opportunities(opportunities)
            
            # Almacenar oportunidades
            await self._store_opportunities(opportunities)
            
            return opportunities[:self.thresholds["max_opportunities"]]
            
        except Exception as e:
            self.logger.error(f"Error rastreando oportunidades: {str(e)}")
            raise
    
    async def start_tracking(
        self,
        interval: int = 3600,  # 1 hora
        criteria: Optional[SearchCriteria] = None
    ):
        """
        Iniciar rastreo continuo de oportunidades.
        
        Args:
            interval: Intervalo en segundos entre chequeos
            criteria: Criterios específicos de búsqueda
        """
        while True:
            try:
                # Obtener paquetes activos
                packages = await self._get_active_packages()
                
                # Rastrear oportunidades
                opportunities = await self.track_opportunities(
                    packages=packages,
                    criteria=criteria
                )
                
                # Procesar oportunidades
                if opportunities:
                    await self._process_opportunities(opportunities)
                
                # Limpiar oportunidades expiradas
                await self._clean_expired_opportunities()
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error en rastreo continuo: {str(e)}")
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    def _is_opportunity(
        self,
        analysis: Dict[str, Any],
        alerts: List[Dict[str, Any]]
    ) -> bool:
        """Determinar si un paquete representa una oportunidad."""
        # Verificar score mínimo
        if analysis["score"] < self.thresholds["min_score"]:
            return False
        
        # Verificar si hay alertas de precio relevantes
        price_drops = [
            alert for alert in alerts
            if alert["type"] == "price_drop"
        ]
        if not price_drops:
            return False
        
        # Verificar ahorro mínimo
        total_savings = sum(
            float(alert["data"]["old_price"]) - float(alert["data"]["new_price"])
            for alert in price_drops
        )
        if total_savings < self.thresholds["min_savings"]:
            return False
        
        return True
    
    async def _create_opportunity(
        self,
        package: TravelPackage,
        analysis: Dict[str, Any],
        alerts: List[Dict[str, Any]]
    ) -> Opportunity:
        """Crear objeto de oportunidad."""
        # Calcular ahorro total
        total_savings = sum(
            float(alert["data"]["old_price"]) - float(alert["data"]["new_price"])
            for alert in alerts
            if alert["type"] == "price_drop"
        )
        
        # Crear oportunidad
        return Opportunity(
            type="package",
            package=package,
            savings=total_savings,
            score=analysis["score"],
            valid_until=datetime.now() + timedelta(
                hours=self.thresholds["expiry_hours"]
            ),
            description=self._generate_description(package, total_savings),
            conditions=self._generate_conditions(package, analysis),
            metadata={
                "analysis": analysis,
                "alerts": alerts
            }
        )
    
    def _prioritize_opportunities(
        self,
        opportunities: List[Opportunity]
    ) -> List[Opportunity]:
        """Priorizar oportunidades según criterios."""
        # Ordenar por puntuación y ahorro
        return sorted(
            opportunities,
            key=lambda x: (x.score, x.savings),
            reverse=True
        )
    
    async def _store_opportunities(self, opportunities: List[Opportunity]):
        """Almacenar oportunidades en base de conocimiento."""
        try:
            for opportunity in opportunities:
                await self.memory.store_opportunity(
                    opportunity.dict()
                )
        except Exception as e:
            self.logger.error(f"Error almacenando oportunidades: {str(e)}")
    
    async def _get_active_packages(self) -> List[TravelPackage]:
        """Obtener paquetes activos para rastrear."""
        try:
            return await self.memory.get_active_packages()
        except Exception as e:
            self.logger.error(f"Error obteniendo paquetes activos: {str(e)}")
            return []
    
    async def _process_opportunities(self, opportunities: List[Opportunity]):
        """Procesar oportunidades detectadas."""
        try:
            for opportunity in opportunities:
                # Log de oportunidad
                self.logger.info(
                    f"Nueva oportunidad detectada: {opportunity.description}"
                )
                
                # Aquí se pueden agregar más acciones como:
                # - Enviar notificaciones
                # - Actualizar dashboards
                # - Generar reportes
                pass
                
        except Exception as e:
            self.logger.error(f"Error procesando oportunidades: {str(e)}")
    
    async def _clean_expired_opportunities(self):
        """Limpiar oportunidades expiradas."""
        try:
            await self.memory.clean_expired_opportunities()
        except Exception as e:
            self.logger.error(f"Error limpiando oportunidades: {str(e)}")
    
    def _generate_description(
        self,
        package: TravelPackage,
        savings: float
    ) -> str:
        """Generar descripción de la oportunidad."""
        return (
            f"¡Oportunidad! {package.title} a {package.destination} "
            f"con ahorro de USD {savings:.2f}"
        )
    
    def _generate_conditions(
        self,
        package: TravelPackage,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Generar condiciones de la oportunidad."""
        conditions = [
            "Sujeto a disponibilidad",
            f"Válido hasta {package.end_date.strftime('%Y-%m-%d')}",
            "Precios pueden variar sin previo aviso"
        ]
        
        if package.cancellation_policy:
            conditions.append(f"Política de cancelación: {package.cancellation_policy}")
            
        return conditions
