"""
Gestor de navegadores automatizados.

Este módulo implementa:
1. Gestión de navegadores
2. Control de sesiones
3. Sistema anti-bloqueo
4. Rotación de proxies
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import asyncio
from prometheus_client import Counter, Gauge
from playwright.async_api import async_playwright, Browser, Page
import aiohttp

from ...schemas import (
    BrowserConfig,
    ProxyConfig,
    BrowserSession,
    AutomationResult
)
from ...metrics import get_metrics_collector

# Métricas
BROWSER_SESSIONS = Gauge(
    'browser_sessions_active',
    'Number of active browser sessions',
    ['browser_type']
)

BROWSER_OPERATIONS = Counter(
    'browser_operations_total',
    'Number of browser operations',
    ['operation_type', 'status']
)

class BrowserManager:
    """
    Gestor de navegadores.
    
    Responsabilidades:
    1. Gestionar navegadores
    2. Controlar sesiones
    3. Manejar proxies
    4. Prevenir bloqueos
    """

    def __init__(
        self,
        browser_config: Optional[BrowserConfig] = None,
        proxy_config: Optional[ProxyConfig] = None
    ):
        """
        Inicializar gestor.
        
        Args:
            browser_config: Configuración de navegadores
            proxy_config: Configuración de proxies
        """
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        
        # Configuración por defecto
        self.browser_config = browser_config or BrowserConfig(
            max_sessions=5,
            session_timeout=300,  # 5 minutos
            retry_attempts=3
        )
        
        self.proxy_config = proxy_config or ProxyConfig(
            enabled=False,
            rotation_interval=300,  # 5 minutos
            max_consecutive_fails=3
        )
        
        # Estado del gestor
        self.active_sessions: Dict[str, BrowserSession] = {}
        self.available_proxies: List[Dict[str, str]] = []
        self.proxy_fails: Dict[str, int] = {}
        
        # Control de sesiones
        self.session_lock = asyncio.Lock()
        self.cleanup_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """Iniciar gestor."""
        # Iniciar tarea de limpieza
        self.cleanup_task = asyncio.create_task(
            self._cleanup_sessions()
        )
        
        # Cargar proxies si están habilitados
        if self.proxy_config.enabled:
            await self._load_proxies()
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar gestor."""
        # Cancelar tarea de limpieza
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Cerrar sesiones activas
        for session in self.active_sessions.values():
            await self._close_session(session.id)

    async def get_session(
        self,
        session_id: Optional[str] = None
    ) -> BrowserSession:
        """
        Obtener sesión de navegador.
        
        Args:
            session_id: ID de sesión opcional
            
        Returns:
            Sesión de navegador
        """
        try:
            async with self.session_lock:
                # Verificar sesión existente
                if session_id and session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                    session.last_used = datetime.now()
                    return session
                
                # Verificar límite de sesiones
                if len(self.active_sessions) >= self.browser_config.max_sessions:
                    # Cerrar sesión más antigua
                    oldest_session = min(
                        self.active_sessions.values(),
                        key=lambda s: s.last_used
                    )
                    await self._close_session(oldest_session.id)
                
                # Crear nueva sesión
                session = await self._create_session()
                self.active_sessions[session.id] = session
                
                # Actualizar métricas
                BROWSER_SESSIONS.labels(
                    browser_type=session.browser_type
                ).inc()
                
                return session
                
        except Exception as e:
            self.logger.error(f"Error obteniendo sesión: {e}")
            raise

    async def execute_action(
        self,
        session_id: str,
        action: str,
        params: Dict[str, Any]
    ) -> AutomationResult:
        """
        Ejecutar acción en navegador.
        
        Args:
            session_id: ID de sesión
            action: Acción a ejecutar
            params: Parámetros de la acción
            
        Returns:
            Resultado de la acción
        """
        try:
            session = await self.get_session(session_id)
            
            # Ejecutar con reintentos
            for attempt in range(self.browser_config.retry_attempts):
                try:
                    # Ejecutar acción
                    result = await self._execute_browser_action(
                        session.page,
                        action,
                        params
                    )
                    
                    # Registrar éxito
                    BROWSER_OPERATIONS.labels(
                        operation_type=action,
                        status="success"
                    ).inc()
                    
                    return result
                    
                except Exception as e:
                    if attempt == self.browser_config.retry_attempts - 1:
                        raise
                    
                    # Rotar proxy si es necesario
                    if self.proxy_config.enabled:
                        await self._rotate_proxy(session)
                    
                    # Reiniciar página
                    await session.page.reload()
            
            raise Exception("Max retry attempts reached")
            
        except Exception as e:
            self.logger.error(f"Error ejecutando acción: {e}")
            
            BROWSER_OPERATIONS.labels(
                operation_type=action,
                status="error"
            ).inc()
            
            return AutomationResult(
                success=False,
                error=str(e)
            )

    async def _create_session(self) -> BrowserSession:
        """Crear nueva sesión de navegador."""
        try:
            # Iniciar playwright
            playwright = await async_playwright().start()
            
            # Configurar proxy si está habilitado
            proxy = await self._get_next_proxy() if self.proxy_config.enabled else None
            
            # Crear navegador
            browser = await playwright.chromium.launch(
                proxy=proxy,
                headless=True
            )
            
            # Crear contexto y página
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Crear sesión
            return BrowserSession(
                id=str(len(self.active_sessions) + 1),
                browser=browser,
                context=context,
                page=page,
                browser_type="chromium",
                proxy=proxy,
                created_at=datetime.now(),
                last_used=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error creando sesión: {e}")
            raise

    async def _close_session(
        self,
        session_id: str
    ) -> None:
        """Cerrar sesión de navegador."""
        try:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Cerrar navegador
                await session.browser.close()
                
                # Actualizar métricas
                BROWSER_SESSIONS.labels(
                    browser_type=session.browser_type
                ).dec()
                
                # Eliminar sesión
                del self.active_sessions[session_id]
                
        except Exception as e:
            self.logger.error(f"Error cerrando sesión: {e}")

    async def _cleanup_sessions(self) -> None:
        """Limpiar sesiones inactivas."""
        try:
            while True:
                await asyncio.sleep(60)  # Verificar cada minuto
                
                current_time = datetime.now()
                
                # Buscar sesiones expiradas
                expired_sessions = [
                    session_id
                    for session_id, session in self.active_sessions.items()
                    if (current_time - session.last_used).total_seconds() >
                    self.browser_config.session_timeout
                ]
                
                # Cerrar sesiones expiradas
                for session_id in expired_sessions:
                    await self._close_session(session_id)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error en limpieza: {e}")

    async def _load_proxies(self) -> None:
        """Cargar lista de proxies."""
        try:
            # TODO: Implementar carga de proxies
            # Por ahora usar lista estática
            self.available_proxies = [
                {"server": "proxy1.example.com:8080"},
                {"server": "proxy2.example.com:8080"}
            ]
            
        except Exception as e:
            self.logger.error(f"Error cargando proxies: {e}")

    async def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Obtener siguiente proxy."""
        try:
            if not self.available_proxies:
                return None
            
            # Rotar lista
            proxy = self.available_proxies.pop(0)
            self.available_proxies.append(proxy)
            
            return proxy
            
        except Exception as e:
            self.logger.error(f"Error obteniendo proxy: {e}")
            return None

    async def _rotate_proxy(
        self,
        session: BrowserSession
    ) -> None:
        """Rotar proxy de sesión."""
        try:
            if not self.proxy_config.enabled:
                return
            
            # Registrar fallo del proxy actual
            if session.proxy:
                proxy_server = session.proxy["server"]
                self.proxy_fails[proxy_server] = (
                    self.proxy_fails.get(proxy_server, 0) + 1
                )
                
                # Remover proxy si excede fallos
                if self.proxy_fails[proxy_server] >= self.proxy_config.max_consecutive_fails:
                    self.available_proxies = [
                        p for p in self.available_proxies
                        if p["server"] != proxy_server
                    ]
            
            # Obtener nuevo proxy
            new_proxy = await self._get_next_proxy()
            
            # Recrear sesión con nuevo proxy
            new_session = await self._create_session()
            
            # Transferir estado
            await self._close_session(session.id)
            self.active_sessions[session.id] = new_session
            
        except Exception as e:
            self.logger.error(f"Error rotando proxy: {e}")

    async def _execute_browser_action(
        self,
        page: Page,
        action: str,
        params: Dict[str, Any]
    ) -> AutomationResult:
        """Ejecutar acción en página."""
        try:
            if action == "navigate":
                await page.goto(params["url"])
                await page.wait_for_load_state("networkidle")
                
            elif action == "click":
                await page.click(params["selector"])
                
            elif action == "type":
                await page.type(
                    params["selector"],
                    params["text"]
                )
                
            elif action == "extract":
                data = await page.eval(
                    params["selector"],
                    params.get("script", "el => el.textContent")
                )
                return AutomationResult(
                    success=True,
                    data=data
                )
            
            return AutomationResult(success=True)
            
        except Exception as e:
            self.logger.error(f"Error ejecutando acción: {e}")
            raise

# Instancia global
browser_manager = BrowserManager()

async def get_browser_manager() -> BrowserManager:
    """Obtener instancia del gestor."""
    return browser_manager
