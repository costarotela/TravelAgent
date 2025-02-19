"""
Dashboard principal del vendedor.

Este módulo implementa:
1. Vista principal del dashboard
2. Control de estado
3. Gestión de eventos
4. Actualización en tiempo real
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from prometheus_client import Counter, Gauge

from ...schemas import (
    DashboardState,
    SessionEvent,
    UIUpdate,
    NotificationLevel
)
from ...metrics import get_metrics_collector
from ...core.session import get_session_manager
from ...core.budget import get_budget_calculator

# Métricas
DASHBOARD_SESSIONS = Gauge(
    'dashboard_active_sessions',
    'Number of active dashboard sessions'
)

DASHBOARD_EVENTS = Counter(
    'dashboard_events_total',
    'Number of dashboard events',
    ['event_type']
)

class DashboardManager:
    """
    Gestor del dashboard.
    
    Responsabilidades:
    1. Gestionar estado
    2. Manejar conexiones
    3. Procesar eventos
    4. Actualizar UI
    """

    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        
        # Estado del dashboard
        self.active_sessions: Dict[str, WebSocket] = {}
        self.session_states: Dict[str, DashboardState] = {}
        
        # Configuración
        self.config = {
            "update_interval": 5,  # 5 segundos
            "max_notifications": 10,
            "auto_refresh": True
        }
        
        # Aplicación FastAPI
        self.app = FastAPI(title="SmartTravelAgent Dashboard")
        self.templates = Jinja2Templates(directory="templates")
        
        # Montar archivos estáticos
        self.app.mount(
            "/static",
            StaticFiles(directory="static"),
            name="static"
        )
        
        # Registrar rutas
        self._register_routes()
        
        # Tarea de actualización
        self.update_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """Iniciar gestor."""
        # Iniciar tarea de actualización
        self.update_task = asyncio.create_task(
            self._update_loop()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar gestor."""
        # Cancelar tarea de actualización
        if self.update_task:
            self.update_task.cancel()
        
        # Cerrar conexiones activas
        for session_id in list(self.active_sessions.keys()):
            await self.disconnect_session(session_id)

    def _register_routes(self) -> None:
        """Registrar rutas de la aplicación."""
        @self.app.get("/")
        async def index():
            """Vista principal."""
            return self.templates.TemplateResponse(
                "index.html",
                {"request": {}}
            )

        @self.app.websocket("/ws/{session_id}")
        async def websocket_endpoint(
            websocket: WebSocket,
            session_id: str
        ):
            """Endpoint WebSocket."""
            await self.connect_session(session_id, websocket)
            
            try:
                while True:
                    # Recibir evento
                    data = await websocket.receive_json()
                    await self.process_event(session_id, data)
                    
            except WebSocketDisconnect:
                await self.disconnect_session(session_id)

    async def connect_session(
        self,
        session_id: str,
        websocket: WebSocket
    ) -> None:
        """
        Conectar nueva sesión.
        
        Args:
            session_id: ID de sesión
            websocket: Conexión WebSocket
        """
        try:
            # Aceptar conexión
            await websocket.accept()
            
            # Registrar sesión
            self.active_sessions[session_id] = websocket
            
            # Crear estado inicial
            self.session_states[session_id] = DashboardState(
                session_id=session_id,
                connected_at=datetime.now(),
                notifications=[],
                current_budget=None,
                is_editing=False
            )
            
            # Actualizar métricas
            DASHBOARD_SESSIONS.inc()
            
            # Enviar estado inicial
            await self.send_update(
                session_id,
                "initial_state",
                self.session_states[session_id].dict()
            )
            
        except Exception as e:
            self.logger.error(f"Error conectando sesión: {e}")
            raise

    async def disconnect_session(
        self,
        session_id: str
    ) -> None:
        """
        Desconectar sesión.
        
        Args:
            session_id: ID de sesión
        """
        try:
            if session_id in self.active_sessions:
                # Cerrar conexión
                await self.active_sessions[session_id].close()
                
                # Limpiar estado
                del self.active_sessions[session_id]
                del self.session_states[session_id]
                
                # Actualizar métricas
                DASHBOARD_SESSIONS.dec()
                
        except Exception as e:
            self.logger.error(f"Error desconectando sesión: {e}")

    async def process_event(
        self,
        session_id: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Procesar evento de sesión.
        
        Args:
            session_id: ID de sesión
            event_data: Datos del evento
        """
        try:
            event = SessionEvent(**event_data)
            
            # Registrar evento
            DASHBOARD_EVENTS.labels(
                event_type=event.type
            ).inc()
            
            # Procesar según tipo
            if event.type == "edit_budget":
                await self._handle_edit_budget(session_id, event)
                
            elif event.type == "save_budget":
                await self._handle_save_budget(session_id, event)
                
            elif event.type == "refresh_data":
                await self._handle_refresh_data(session_id, event)
                
            elif event.type == "update_config":
                await self._handle_update_config(session_id, event)
            
        except Exception as e:
            self.logger.error(f"Error procesando evento: {e}")
            
            # Notificar error
            await self.add_notification(
                session_id,
                "Error procesando evento",
                str(e),
                NotificationLevel.ERROR
            )

    async def send_update(
        self,
        session_id: str,
        update_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Enviar actualización a sesión.
        
        Args:
            session_id: ID de sesión
            update_type: Tipo de actualización
            data: Datos a enviar
        """
        try:
            if session_id not in self.active_sessions:
                return
            
            # Crear actualización
            update = UIUpdate(
                type=update_type,
                timestamp=datetime.now(),
                data=data
            )
            
            # Enviar por WebSocket
            await self.active_sessions[session_id].send_json(
                update.dict()
            )
            
        except Exception as e:
            self.logger.error(f"Error enviando actualización: {e}")

    async def add_notification(
        self,
        session_id: str,
        title: str,
        message: str,
        level: NotificationLevel
    ) -> None:
        """
        Agregar notificación.
        
        Args:
            session_id: ID de sesión
            title: Título
            message: Mensaje
            level: Nivel
        """
        try:
            if session_id not in self.session_states:
                return
            
            state = self.session_states[session_id]
            
            # Agregar notificación
            state.notifications.append({
                "title": title,
                "message": message,
                "level": level,
                "timestamp": datetime.now()
            })
            
            # Mantener límite
            if len(state.notifications) > self.config["max_notifications"]:
                state.notifications.pop(0)
            
            # Enviar actualización
            await self.send_update(
                session_id,
                "notifications",
                {"notifications": state.notifications}
            )
            
        except Exception as e:
            self.logger.error(f"Error agregando notificación: {e}")

    async def _update_loop(self) -> None:
        """Loop de actualización periódica."""
        try:
            while True:
                # Esperar intervalo
                await asyncio.sleep(self.config["update_interval"])
                
                # Actualizar sesiones activas
                for session_id in list(self.active_sessions.keys()):
                    try:
                        await self._update_session(session_id)
                    except Exception as e:
                        self.logger.error(
                            f"Error actualizando sesión {session_id}: {e}"
                        )
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error en loop de actualización: {e}")

    async def _update_session(
        self,
        session_id: str
    ) -> None:
        """Actualizar estado de sesión."""
        try:
            state = self.session_states[session_id]
            
            # Obtener datos actualizados
            if state.current_budget and not state.is_editing:
                session_manager = await get_session_manager()
                budget_calculator = await get_budget_calculator()
                
                # Verificar cambios
                session = await session_manager.get_session(
                    state.current_budget.session_id
                )
                
                if session and session.budget != state.current_budget:
                    # Recalcular presupuesto
                    result = await budget_calculator.calculate_budget(
                        session.budget.packages
                    )
                    
                    if result.success:
                        # Actualizar estado
                        state.current_budget = result.budget
                        
                        # Enviar actualización
                        await self.send_update(
                            session_id,
                            "budget_updated",
                            {"budget": result.budget.dict()}
                        )
            
        except Exception as e:
            self.logger.error(f"Error actualizando sesión: {e}")

    async def _handle_edit_budget(
        self,
        session_id: str,
        event: SessionEvent
    ) -> None:
        """Manejar edición de presupuesto."""
        try:
            state = self.session_states[session_id]
            
            # Marcar como editando
            state.is_editing = True
            
            # Enviar actualización
            await self.send_update(
                session_id,
                "edit_mode",
                {"is_editing": True}
            )
            
        except Exception as e:
            self.logger.error(f"Error manejando edición: {e}")
            raise

    async def _handle_save_budget(
        self,
        session_id: str,
        event: SessionEvent
    ) -> None:
        """Manejar guardado de presupuesto."""
        try:
            state = self.session_states[session_id]
            
            # Actualizar presupuesto
            session_manager = await get_session_manager()
            
            success = await session_manager.update_session(
                state.current_budget.session_id,
                event.data["budget"],
                "Manual update from dashboard"
            )
            
            if success:
                # Actualizar estado
                state.is_editing = False
                state.current_budget = event.data["budget"]
                
                # Notificar éxito
                await self.add_notification(
                    session_id,
                    "Presupuesto actualizado",
                    "Los cambios se guardaron correctamente",
                    NotificationLevel.SUCCESS
                )
                
            else:
                raise Exception("Error guardando presupuesto")
            
        except Exception as e:
            self.logger.error(f"Error guardando presupuesto: {e}")
            raise

    async def _handle_refresh_data(
        self,
        session_id: str,
        event: SessionEvent
    ) -> None:
        """Manejar actualización de datos."""
        try:
            state = self.session_states[session_id]
            
            if not state.current_budget:
                return
            
            # Recalcular presupuesto
            budget_calculator = await get_budget_calculator()
            
            result = await budget_calculator.calculate_budget(
                state.current_budget.packages,
                force_refresh=True
            )
            
            if result.success:
                # Actualizar estado
                state.current_budget = result.budget
                
                # Enviar actualización
                await self.send_update(
                    session_id,
                    "budget_updated",
                    {"budget": result.budget.dict()}
                )
                
                # Notificar éxito
                await self.add_notification(
                    session_id,
                    "Datos actualizados",
                    "Se obtuvieron nuevos datos de proveedores",
                    NotificationLevel.INFO
                )
                
            else:
                raise Exception("Error actualizando datos")
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos: {e}")
            raise

    async def _handle_update_config(
        self,
        session_id: str,
        event: SessionEvent
    ) -> None:
        """Manejar actualización de configuración."""
        try:
            # Actualizar configuración
            for key, value in event.data.items():
                if key in self.config:
                    self.config[key] = value
            
            # Notificar cambio
            await self.add_notification(
                session_id,
                "Configuración actualizada",
                "Los cambios se aplicaron correctamente",
                NotificationLevel.SUCCESS
            )
            
        except Exception as e:
            self.logger.error(f"Error actualizando configuración: {e}")
            raise

# Instancia global
dashboard_manager = DashboardManager()

def run_dashboard(
    host: str = "0.0.0.0",
    port: int = 8000
) -> None:
    """Ejecutar dashboard."""
    uvicorn.run(
        dashboard_manager.app,
        host=host,
        port=port
    )
