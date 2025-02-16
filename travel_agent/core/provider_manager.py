"""
Gestor de proveedores de viajes.

Este módulo se encarga de:
1. Gestionar proveedores
2. Coordinar búsquedas
3. Procesar reservas
4. Mantener credenciales
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from .schemas import TravelPackage, SearchCriteria, Provider, Booking, BookingStatus
from .browser_manager import BrowserManager
from ..memory.supabase import SupabaseMemory


class ProviderManager:
    """Gestor de proveedores de viajes."""

    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()
        self.browser = BrowserManager()

        # Proveedores activos
        self.providers: Dict[str, Provider] = {}

        # Estado del gestor
        self.active = False
        self.last_update = datetime.now()

        # Configuración
        self.config = {
            "search_timeout": 300,  # 5 minutos
            "booking_timeout": 600,  # 10 minutos
            "max_retries": 3,
            "concurrent_searches": 3,
        }

    async def start(self):
        """Iniciar gestor."""
        try:
            self.active = True

            # Inicializar browser
            await self.browser.initialize()

            # Cargar proveedores
            await self.load_providers()

            self.logger.info("Gestor de proveedores iniciado")

        except Exception as e:
            self.logger.error(f"Error iniciando gestor: {str(e)}")
            raise

    async def stop(self):
        """Detener gestor."""
        try:
            self.active = False

            # Detener browser
            await self.browser.cleanup()

            # Limpiar proveedores
            self.providers.clear()

            self.logger.info("Gestor de proveedores detenido")

        except Exception as e:
            self.logger.error(f"Error deteniendo gestor: {str(e)}")
            raise

    async def load_providers(self):
        """Cargar proveedores disponibles."""
        try:
            # Obtener proveedores de la base de conocimiento
            providers_data = await self.memory.get_providers()

            for provider_data in providers_data:
                provider = Provider(**provider_data)
                self.providers[provider.id] = provider

            self.logger.info(f"Proveedores cargados: {len(self.providers)}")

        except Exception as e:
            self.logger.error(f"Error cargando proveedores: {str(e)}")
            raise

    async def search_packages(
        self, criteria: SearchCriteria, providers: Optional[List[str]] = None
    ) -> List[TravelPackage]:
        """
        Buscar paquetes en proveedores.

        Args:
            criteria: Criterios de búsqueda
            providers: IDs de proveedores específicos

        Returns:
            Lista de paquetes encontrados
        """
        try:
            # Determinar proveedores a usar
            target_providers = [
                p for p in self.providers.values() if not providers or p.id in providers
            ]

            if not target_providers:
                raise ValueError("No hay proveedores disponibles")

            # Crear tareas de búsqueda
            search_tasks = []
            for provider in target_providers:
                task = asyncio.create_task(
                    self._search_provider(provider=provider, criteria=criteria)
                )
                search_tasks.append(task)

            # Ejecutar búsquedas en paralelo
            results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # Procesar resultados
            packages = []
            for provider_packages in results:
                if isinstance(provider_packages, Exception):
                    self.logger.error(f"Error en búsqueda: {str(provider_packages)}")
                    continue

                packages.extend(provider_packages)

            return packages

        except Exception as e:
            self.logger.error(f"Error buscando paquetes: {str(e)}")
            raise

    async def process_booking(
        self, package: TravelPackage, metadata: Optional[Dict[str, Any]] = None
    ) -> Booking:
        """
        Procesar reserva de paquete.

        Args:
            package: Paquete a reservar
            metadata: Metadatos adicionales

        Returns:
            Reserva procesada
        """
        try:
            # Obtener proveedor
            provider = self.providers.get(package.provider_id)
            if not provider:
                raise ValueError(f"Proveedor no encontrado: {package.provider_id}")

            # Verificar disponibilidad
            availability = await self._check_availability(
                provider=provider, package=package
            )

            if not availability["available"]:
                raise ValueError(f"Paquete no disponible: {package.id}")

            # Procesar reserva
            booking = await self._process_provider_booking(
                provider=provider, package=package, metadata=metadata
            )

            # Almacenar reserva
            await self._store_booking(booking)

            return booking

        except Exception as e:
            self.logger.error(f"Error procesando reserva: {str(e)}")
            raise

    async def get_provider(self, provider_id: str) -> Optional[Provider]:
        """
        Obtener proveedor por ID.

        Args:
            provider_id: ID del proveedor

        Returns:
            Proveedor solicitado
        """
        return self.providers.get(provider_id)

    async def update_provider(self, provider_id: str, data: Dict[str, Any]) -> Provider:
        """
        Actualizar datos de proveedor.

        Args:
            provider_id: ID del proveedor
            data: Nuevos datos

        Returns:
            Proveedor actualizado
        """
        try:
            provider = self.providers.get(provider_id)
            if not provider:
                raise ValueError(f"Proveedor no encontrado: {provider_id}")

            # Actualizar datos
            for key, value in data.items():
                setattr(provider, key, value)

            # Almacenar cambios
            await self._store_provider(provider)

            return provider

        except Exception as e:
            self.logger.error(f"Error actualizando proveedor: {str(e)}")
            raise

    async def _search_provider(
        self, provider: Provider, criteria: SearchCriteria
    ) -> List[TravelPackage]:
        """Buscar paquetes en proveedor específico."""
        try:
            self.logger.info(f"Buscando en proveedor: {provider.name}")

            # Obtener página de búsqueda
            page = await self.browser.new_page()

            # Configurar interceptores
            await self._setup_interceptors(page, provider)

            # Navegar a URL de búsqueda
            await page.goto(provider.search_url)

            # Aplicar criterios de búsqueda
            await self._apply_search_criteria(page, criteria, provider)

            # Extraer resultados
            packages = await self._extract_search_results(page, provider)

            # Cerrar página
            await page.close()

            return packages

        except Exception as e:
            self.logger.error(f"Error buscando en proveedor {provider.name}: {str(e)}")
            return []

    async def _process_provider_booking(
        self,
        provider: Provider,
        package: TravelPackage,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Booking:
        """Procesar reserva con proveedor específico."""
        try:
            self.logger.info(f"Procesando reserva con proveedor: {provider.name}")

            # Obtener página de reserva
            page = await self.browser.new_page()

            # Configurar interceptores
            await self._setup_interceptors(page, provider)

            # Navegar a URL de reserva
            booking_url = self._get_booking_url(provider, package)
            await page.goto(booking_url)

            # Procesar formulario de reserva
            booking_data = await self._process_booking_form(
                page=page, provider=provider, package=package, metadata=metadata
            )

            # Crear reserva
            booking = Booking(
                id=booking_data["booking_id"],
                provider_id=provider.id,
                package_id=package.id,
                status=BookingStatus.CONFIRMED,
                confirmation_code=booking_data["confirmation_code"],
                booking_date=datetime.now(),
                metadata=metadata or {},
            )

            # Cerrar página
            await page.close()

            return booking

        except Exception as e:
            self.logger.error(
                f"Error procesando reserva con proveedor {provider.name}: {str(e)}"
            )
            raise

    async def _check_availability(
        self, provider: Provider, package: TravelPackage
    ) -> Dict[str, Any]:
        """Verificar disponibilidad de paquete."""
        try:
            # Obtener página de disponibilidad
            page = await self.browser.new_page()

            # Configurar interceptores
            await self._setup_interceptors(page, provider)

            # Navegar a URL del paquete
            await page.goto(package.url)

            # Verificar disponibilidad
            available = await self._check_package_availability(
                page=page, provider=provider, package=package
            )

            # Cerrar página
            await page.close()

            return {"available": available, "checked_at": datetime.now()}

        except Exception as e:
            self.logger.error(f"Error verificando disponibilidad: {str(e)}")
            return {"available": False}

    async def _setup_interceptors(self, page: Any, provider: Provider):
        """Configurar interceptores de red."""
        try:
            # Interceptar requests
            await page.route(
                "**/*",
                lambda route: self._handle_request(route=route, provider=provider),
            )

            # Interceptar responses
            await page.on(
                "response",
                lambda response: self._handle_response(
                    response=response, provider=provider
                ),
            )

        except Exception as e:
            self.logger.error(f"Error configurando interceptores: {str(e)}")
            raise

    async def _handle_request(self, route: Any, provider: Provider):
        """Manejar request interceptado."""
        try:
            # Verificar credenciales
            if provider.requires_auth:
                await self._inject_credentials(route, provider)

            # Continuar request
            await route.continue_()

        except Exception as e:
            self.logger.error(f"Error manejando request: {str(e)}")
            await route.abort()

    async def _handle_response(self, response: Any, provider: Provider):
        """Manejar response interceptado."""
        try:
            # Verificar errores
            if response.status >= 400:
                self.logger.error(
                    f"Error en response de {provider.name}: "
                    f"Status {response.status}"
                )

            # Procesar datos si es necesario
            if response.headers.get("content-type", "").startswith("application/json"):
                data = await response.json()
                await self._process_response_data(data, provider)

        except Exception as e:
            self.logger.error(f"Error manejando response: {str(e)}")

    async def _inject_credentials(self, route: Any, provider: Provider):
        """Inyectar credenciales en request."""
        try:
            # Obtener credenciales
            credentials = await self._get_provider_credentials(provider)

            # Modificar headers
            headers = route.request.headers
            headers["Authorization"] = f"Bearer {credentials['token']}"

            # Actualizar request
            await route.continue_(headers=headers)

        except Exception as e:
            self.logger.error(f"Error inyectando credenciales: {str(e)}")
            raise

    async def _get_provider_credentials(self, provider: Provider) -> Dict[str, str]:
        """Obtener credenciales de proveedor."""
        try:
            # Obtener de base de conocimiento
            credentials = await self.memory.get_provider_credentials(provider.id)

            if not credentials:
                raise ValueError(f"Credenciales no encontradas para: {provider.name}")

            return credentials

        except Exception as e:
            self.logger.error(f"Error obteniendo credenciales: {str(e)}")
            raise

    async def _store_provider(self, provider: Provider):
        """Almacenar proveedor en base de conocimiento."""
        try:
            await self.memory.store_provider(provider.dict())

        except Exception as e:
            self.logger.error(f"Error almacenando proveedor: {str(e)}")
            raise

    async def _store_booking(self, booking: Booking):
        """Almacenar reserva en base de conocimiento."""
        try:
            await self.memory.store_booking(booking.dict())

        except Exception as e:
            self.logger.error(f"Error almacenando reserva: {str(e)}")
            raise
