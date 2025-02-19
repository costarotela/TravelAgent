"""
Agente principal del sistema de viajes.

Este módulo implementa el agente principal que:
1. Coordina todos los componentes
2. Maneja el flujo de trabajo
3. Procesa solicitudes
4. Gestiona el estado global
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from .schemas import SearchCriteria, TravelPackage, Budget, Opportunity, Recommendation
from .session_manager import SessionManager
from .package_analyzer import PackageAnalyzer
from .price_monitor import PriceMonitor
from .opportunity_tracker import OpportunityTracker
from .recommendation_engine import RecommendationEngine
from .browser_manager import BrowserManager
from .provider_manager import ProviderManager
from .budget_engine import BudgetEngine
from .storage_manager import StorageManager
from ..memory.supabase import SupabaseMemory


class SmartTravelAgent:
    """Agente principal del sistema de viajes."""

    def __init__(self):
        """Inicializar agente."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Componentes core
        self.session_manager = SessionManager()
        self.analyzer = PackageAnalyzer()
        self.price_monitor = PriceMonitor()
        self.opportunity_tracker = OpportunityTracker()
        self.recommendation_engine = RecommendationEngine()
        self.browser_manager = BrowserManager()
        self.provider_manager = ProviderManager()
        self.budget_engine = BudgetEngine()
        self.storage = StorageManager()

        # Estado del agente
        self.active = False
        self.current_session: Optional[str] = None
        self.last_update = datetime.now()

    async def start(self):
        """Iniciar agente."""
        try:
            self.active = True
            self.logger.info("Agente iniciado")

            # Iniciar componentes
            await self._initialize_components()

            # Iniciar monitores
            asyncio.create_task(self._monitor_opportunities())
            asyncio.create_task(self._monitor_prices())

        except Exception as e:
            self.logger.error(f"Error iniciando agente: {str(e)}")
            raise

    async def stop(self):
        """Detener agente."""
        try:
            self.active = False

            # Cerrar sesión actual si existe
            if self.current_session:
                await self.session_manager.close_session(
                    session_id=self.current_session, status="agent_stopped"
                )

            # Detener componentes
            await self._stop_components()

            self.logger.info("Agente detenido")

        except Exception as e:
            self.logger.error(f"Error deteniendo agente: {str(e)}")
            raise

    async def process_search(
        self, criteria: SearchCriteria, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesar búsqueda de paquetes.

        Args:
            criteria: Criterios de búsqueda
            metadata: Metadatos adicionales

        Returns:
            Resultados del proceso
        """
        try:
            # Crear nueva sesión
            session_id = await self.session_manager.create_session(
                criteria=criteria, metadata=metadata
            )
            self.current_session = session_id

            # Buscar paquetes en proveedores
            packages = await self.provider_manager.search_packages(criteria=criteria)

            # Analizar paquetes
            analysis = await self.analyzer.analyze_packages(
                packages=packages, criteria=criteria
            )

            # Obtener recomendaciones
            recommendations = await self.recommendation_engine.get_recommendations(
                packages=packages, criteria=criteria
            )

            # Rastrear oportunidades
            opportunities = await self.opportunity_tracker.track_opportunities(
                packages=packages, criteria=criteria
            )

            # Actualizar sesión
            await self.session_manager.update_session(
                session_id=session_id,
                packages=packages,
                metadata={
                    "analysis": analysis,
                    "recommendations": [r.dict() for r in recommendations],
                    "opportunities": [o.dict() for o in opportunities],
                },
            )

            return {
                "session_id": session_id,
                "packages": [p.dict() for p in packages],
                "analysis": analysis,
                "recommendations": [r.dict() for r in recommendations],
                "opportunities": [o.dict() for o in opportunities],
            }

        except Exception as e:
            self.logger.error(f"Error procesando búsqueda: {str(e)}")
            raise

    async def create_budget(
        self,
        session_id: str,
        packages: List[TravelPackage],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Budget:
        """
        Crear presupuesto para paquetes.

        Args:
            session_id: ID de sesión
            packages: Paquetes a incluir
            metadata: Metadatos adicionales

        Returns:
            Presupuesto generado
        """
        try:
            # Verificar sesión
            session = await self.session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Sesión no encontrada: {session_id}")

            # Generar presupuesto
            budget = await self.budget_engine.create_budget(
                packages=packages, metadata=metadata
            )

            # Agregar a sesión
            await self.session_manager.add_budget_to_session(
                session_id=session_id, budget=budget
            )

            # Almacenar presupuesto
            await self.storage.store_budget(budget)

            return budget

        except Exception as e:
            self.logger.error(f"Error creando presupuesto: {str(e)}")
            raise

    async def process_booking(
        self, session_id: str, budget_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesar reserva de paquete.

        Args:
            session_id: ID de sesión
            budget_id: ID de presupuesto
            metadata: Metadatos adicionales

        Returns:
            Resultado del proceso
        """
        try:
            # Verificar sesión y presupuesto
            session = await self.session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Sesión no encontrada: {session_id}")

            budget = await self.storage.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto no encontrado: {budget_id}")

            # Procesar reserva con proveedor
            booking = await self.provider_manager.process_booking(
                budget=budget, metadata=metadata
            )

            # Actualizar sesión
            await self.session_manager.add_to_history(
                session_id=session_id,
                action="booking_processed",
                data={"budget_id": budget_id, "booking": booking},
            )

            # Cerrar sesión
            await self.session_manager.close_session(
                session_id=session_id, status="completed"
            )

            return booking

        except Exception as e:
            self.logger.error(f"Error procesando reserva: {str(e)}")
            raise

    async def _initialize_components(self):
        """Inicializar componentes del agente."""
        try:
            # Iniciar browser manager
            await self.browser_manager.initialize()

            # Cargar proveedores
            await self.provider_manager.load_providers()

            # Iniciar storage
            await self.storage.initialize()

        except Exception as e:
            self.logger.error(f"Error inicializando componentes: {str(e)}")
            raise

    async def _stop_components(self):
        """Detener componentes del agente."""
        try:
            # Detener browser manager
            await self.browser_manager.cleanup()

            # Detener proveedores
            await self.provider_manager.cleanup()

            # Detener storage
            await self.storage.cleanup()

        except Exception as e:
            self.logger.error(f"Error deteniendo componentes: {str(e)}")
            raise

    async def _monitor_opportunities(self):
        """Monitor continuo de oportunidades."""
        while self.active:
            try:
                if self.current_session:
                    session = await self.session_manager.get_session(
                        self.current_session
                    )
                    if session and session["packages"]:
                        packages = [TravelPackage(**p) for p in session["packages"]]
                        criteria = SearchCriteria(**session["criteria"])

                        opportunities = (
                            await self.opportunity_tracker.track_opportunities(
                                packages=packages, criteria=criteria
                            )
                        )

                        if opportunities:
                            await self.session_manager.update_session(
                                session_id=self.current_session,
                                metadata={
                                    "opportunities": [o.dict() for o in opportunities]
                                },
                            )

                await asyncio.sleep(300)  # 5 minutos

            except Exception as e:
                self.logger.error(f"Error en monitor de oportunidades: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_prices(self):
        """Monitor continuo de precios."""
        while self.active:
            try:
                if self.current_session:
                    session = await self.session_manager.get_session(
                        self.current_session
                    )
                    if session and session["packages"]:
                        packages = [TravelPackage(**p) for p in session["packages"]]

                        for package in packages:
                            alerts = await self.price_monitor.monitor_package(
                                package=package, track_changes=True
                            )

                            if alerts:
                                await self.session_manager.add_to_history(
                                    session_id=self.current_session,
                                    action="price_alerts",
                                    data={"alerts": alerts},
                                )

                await asyncio.sleep(600)  # 10 minutos

            except Exception as e:
                self.logger.error(f"Error en monitor de precios: {str(e)}")
                await asyncio.sleep(60)
