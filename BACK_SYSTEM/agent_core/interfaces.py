"""
Interfaces base del agente de viajes.
Define contratos y protocolos de comunicación.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol
from datetime import datetime
from .schemas import (
    TravelPackage,
    SearchCriteria,
    CustomerProfile,
    SalesQuery,
    Activity,
    Accommodation,
    AnalysisResult
)

class DataProvider(Protocol):
    """Protocolo para proveedores de datos."""
    
    def search_packages(
        self,
        criteria: SearchCriteria,
        limit: Optional[int] = None
    ) -> List[TravelPackage]:
        """Buscar paquetes según criterios."""
        ...
    
    def get_package_details(
        self,
        package_id: str
    ) -> Optional[TravelPackage]:
        """Obtener detalles de un paquete específico."""
        ...
    
    def get_price_history(
        self,
        package_id: str
    ) -> List[Dict[str, Any]]:
        """Obtener historial de precios."""
        ...

class AnalysisEngine(Protocol):
    """Protocolo para motores de análisis."""
    
    def analyze_package(
        self,
        package: TravelPackage,
        context: Dict[str, Any]
    ) -> AnalysisResult:
        """Analizar un paquete turístico."""
        ...
    
    def compare_packages(
        self,
        packages: List[TravelPackage]
    ) -> Dict[str, Any]:
        """Comparar múltiples paquetes."""
        ...
    
    def get_insights(
        self,
        data: Dict[str, Any]
    ) -> List[str]:
        """Generar insights desde datos."""
        ...

class RecommendationEngine(Protocol):
    """Protocolo para motor de recomendaciones."""
    
    def get_recommendations(
        self,
        customer: CustomerProfile,
        criteria: SearchCriteria,
        available_packages: List[TravelPackage]
    ) -> List[TravelPackage]:
        """Generar recomendaciones personalizadas."""
        ...
    
    def rank_packages(
        self,
        packages: List[TravelPackage],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rankear paquetes según relevancia."""
        ...
    
    def explain_recommendation(
        self,
        package: TravelPackage,
        context: Dict[str, Any]
    ) -> List[str]:
        """Explicar razones de una recomendación."""
        ...

class CacheManager(Protocol):
    """Protocolo para gestor de caché."""
    
    def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Obtener valor de caché."""
        ...
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Guardar valor en caché."""
        ...
    
    def delete(
        self,
        key: str
    ) -> None:
        """Eliminar valor de caché."""
        ...
    
    def clear(self) -> None:
        """Limpiar toda la caché."""
        ...

class StorageManager(Protocol):
    """Protocolo para gestor de almacenamiento."""
    
    def save(
        self,
        collection: str,
        data: Dict[str, Any]
    ) -> str:
        """Guardar datos."""
        ...
    
    def get(
        self,
        collection: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener datos."""
        ...
    
    def update(
        self,
        collection: str,
        id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Actualizar datos."""
        ...
    
    def delete(
        self,
        collection: str,
        id: str
    ) -> bool:
        """Eliminar datos."""
        ...

class EventEmitter(Protocol):
    """Protocolo para emisor de eventos."""
    
    def emit(
        self,
        event: str,
        data: Dict[str, Any]
    ) -> None:
        """Emitir evento."""
        ...
    
    def subscribe(
        self,
        event: str,
        handler: callable
    ) -> None:
        """Suscribirse a evento."""
        ...
    
    def unsubscribe(
        self,
        event: str,
        handler: callable
    ) -> None:
        """Desuscribirse de evento."""
        ...

class MetricsCollector(Protocol):
    """Protocolo para recolector de métricas."""
    
    def record(
        self,
        metric: str,
        value: Any,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Registrar métrica."""
        ...
    
    def increment(
        self,
        metric: str,
        value: int = 1,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Incrementar contador."""
        ...
    
    def timing(
        self,
        metric: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Registrar tiempo."""
        ...

class Logger(Protocol):
    """Protocolo para logger."""
    
    def debug(
        self,
        message: str,
        **kwargs: Any
    ) -> None:
        """Log debug message."""
        ...
    
    def info(
        self,
        message: str,
        **kwargs: Any
    ) -> None:
        """Log info message."""
        ...
    
    def warning(
        self,
        message: str,
        **kwargs: Any
    ) -> None:
        """Log warning message."""
        ...
    
    def error(
        self,
        message: str,
        **kwargs: Any
    ) -> None:
        """Log error message."""
        ...

class AgentComponent(ABC):
    """Clase base para componentes del agente."""
    
    def __init__(
        self,
        logger: Logger,
        metrics: MetricsCollector,
        events: EventEmitter
    ):
        self.logger = logger
        self.metrics = metrics
        self.events = events
    
    @abstractmethod
    async def initialize(self) -> None:
        """Inicializar componente."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Apagar componente."""
        pass
    
    def emit_event(
        self,
        event: str,
        data: Dict[str, Any]
    ) -> None:
        """Emitir evento con logging."""
        self.logger.debug(f"Emitting event: {event}", data=data)
        self.events.emit(event, data)
    
    def record_metric(
        self,
        metric: str,
        value: Any,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Registrar métrica con logging."""
        self.logger.debug(
            f"Recording metric: {metric}",
            value=value,
            tags=tags
        )
        self.metrics.record(metric, value, tags)

class AgentInterface(Protocol):
    """Interfaz principal del agente."""
    
    async def process_query(
        self,
        query: SalesQuery
    ) -> Dict[str, Any]:
        """Procesar consulta de venta."""
        ...
    
    async def get_recommendations(
        self,
        customer: CustomerProfile,
        criteria: SearchCriteria
    ) -> List[TravelPackage]:
        """Obtener recomendaciones."""
        ...
    
    async def analyze_package(
        self,
        package_id: str
    ) -> AnalysisResult:
        """Analizar paquete específico."""
        ...
    
    async def track_interaction(
        self,
        customer_id: str,
        interaction_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Registrar interacción."""
        ...
