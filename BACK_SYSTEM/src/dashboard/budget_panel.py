"""Controlador del panel de presupuestos."""

from typing import Dict, List, Any
from fastapi import APIRouter, WebSocket, Depends
from datetime import datetime

from agent_core.managers.session_budget_manager import SessionBudgetManager, get_budget_manager
from smart_travel_agency.core.recommendation_engine import RecommendationEngine
from smart_travel_agency.core.package_analyzer import PackageAnalyzer

router = APIRouter()

class BudgetPanelController:
    """Controlador para el panel de presupuestos."""
    
    def __init__(
        self,
        budget_manager: SessionBudgetManager,
        recommendation_engine: RecommendationEngine,
        package_analyzer: PackageAnalyzer
    ):
        self.budget_manager = budget_manager
        self.recommendation_engine = recommendation_engine
        self.package_analyzer = package_analyzer
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Obtener datos de la sesión."""
        session_data = await self.budget_manager.get_budget(session_id)
        
        # Enriquecer con recomendaciones y alternativas
        recommendations = await self.recommendation_engine.get_recommendations(session_data)
        alternatives = await self.package_analyzer.get_alternatives(session_data)
        
        return {
            "session_id": session_id,
            "customer_name": session_data["customer_id"],
            "session_start": session_data["start_time"],
            "packages": session_data["packages"],
            "recommendations": recommendations,
            "alternatives": alternatives
        }

    async def connect_websocket(self, websocket: WebSocket, session_id: str):
        """Conectar cliente WebSocket."""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        
        self.active_connections[session_id].append(websocket)
        
        try:
            while True:
                data = await websocket.receive_json()
                await self.handle_websocket_message(session_id, data)
        except:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def handle_websocket_message(self, session_id: str, message: Dict[str, Any]):
        """Manejar mensaje WebSocket."""
        msg_type = message.get("type")
        
        if msg_type == "modify_package":
            await self.modify_package(session_id, message["package_id"], message["modifications"])
        elif msg_type == "apply_recommendation":
            await self.apply_recommendation(session_id, message["recommendation_id"])
        elif msg_type == "preview_alternative":
            await self.preview_alternative(session_id, message["alternative_id"])

    async def notify_session_clients(self, session_id: str, message: Dict[str, Any]):
        """Notificar a todos los clientes de una sesión."""
        if session_id in self.active_connections:
            for ws in self.active_connections[session_id]:
                try:
                    await ws.send_json(message)
                except:
                    continue

    async def modify_package(self, session_id: str, package_id: str, modifications: Dict[str, Any]):
        """Modificar un paquete."""
        # Aplicar modificaciones
        await self.budget_manager.add_modification(session_id, {
            "package_id": package_id,
            "modifications": modifications,
            "timestamp": datetime.now().isoformat()
        })
        
        # Obtener nuevas recomendaciones y alternativas
        session_data = await self.budget_manager.get_budget(session_id)
        recommendations = await self.recommendation_engine.get_recommendations(session_data)
        alternatives = await self.package_analyzer.get_alternatives(session_data)
        
        # Notificar a clientes
        await self.notify_session_clients(session_id, {
            "type": "update",
            "content": {
                "packages": session_data["packages"],
                "recommendations": recommendations,
                "alternatives": alternatives
            }
        })

    async def apply_recommendation(self, session_id: str, recommendation_id: str):
        """Aplicar una recomendación."""
        # Obtener y aplicar recomendación
        recommendation = await self.recommendation_engine.get_recommendation(recommendation_id)
        modifications = recommendation.get_modifications()
        
        # Aplicar modificaciones
        await self.modify_package(session_id, modifications["package_id"], modifications["changes"])

    async def preview_alternative(self, session_id: str, alternative_id: str):
        """Previsualizar una alternativa."""
        # Obtener alternativa
        alternative = await self.package_analyzer.get_alternative(alternative_id)
        
        # Notificar a clientes
        await self.notify_session_clients(session_id, {
            "type": "preview",
            "content": alternative.dict()
        })

# Rutas
@router.get("/budget/{session_id}")
async def get_budget_panel(
    session_id: str,
    controller: BudgetPanelController = Depends()
):
    """Obtener datos del panel de presupuestos."""
    return await controller.get_session_data(session_id)

@router.websocket("/ws/budget/{session_id}")
async def budget_websocket(
    websocket: WebSocket,
    session_id: str,
    controller: BudgetPanelController = Depends()
):
    """Endpoint WebSocket para actualizaciones en tiempo real."""
    await controller.connect_websocket(websocket, session_id)
