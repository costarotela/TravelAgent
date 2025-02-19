"""
Modelos de datos centrales del agente de viajes.
Implementa validación avanzada y documentación detallada.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, field_validator, Field, ValidationInfo
import json

class AccommodationType(str, Enum):
    """Tipos de alojamiento soportados."""
    HOTEL = "hotel"
    RESORT = "resort"
    APARTMENT = "apartment"
    HOSTEL = "hostel"
    VILLA = "villa"
    CABIN = "cabin"
    OTHER = "other"

class ActivityDifficulty(str, Enum):
    """Niveles de dificultad para actividades."""
    EASY = "easy"
    MODERATE = "moderate"
    CHALLENGING = "challenging"
    EXPERT = "expert"

class PackageStatus(str, Enum):
    """Estados posibles de un paquete."""
    AVAILABLE = "available"
    LIMITED = "limited"
    SOLD_OUT = "sold_out"
    PENDING = "pending"
    EXPIRED = "expired"

class PriorityLevel(str, Enum):
    """Niveles de prioridad."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class Location(BaseModel):
    """
    Información detallada de ubicación.
    
    Attributes:
        country: País
        city: Ciudad
        address: Dirección completa
        latitude: Latitud (opcional)
        longitude: Longitud (opcional)
    """
    country: str
    city: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @field_validator('latitude', 'longitude')
    def validate_coordinates(cls, v):
        if v is not None and not -180 <= v <= 180:
            raise ValueError('Coordenada debe estar entre -180 y 180')
        return v

class Accommodation(BaseModel):
    """
    Información detallada de alojamiento.
    
    Attributes:
        name: Nombre del alojamiento
        type: Tipo de alojamiento
        rating: Calificación (0-5)
        stars: Categoría en estrellas (0-5)
        location: Información de ubicación
        amenities: Lista de comodidades
        room_types: Tipos de habitación disponibles
        images: URLs de imágenes
        description: Descripción detallada
        policies: Políticas del alojamiento
    """
    name: str
    type: AccommodationType
    rating: float = Field(..., ge=0, le=5)
    stars: int = Field(..., ge=0, le=5)
    location: Location
    amenities: List[str] = []
    room_types: List[str] = []
    images: List[str] = []
    description: Optional[str] = None
    policies: Dict[str, str] = {}

    @field_validator('rating')
    def validate_rating(cls, v):
        """Validar que el rating sea un número válido."""
        if not isinstance(v, (int, float)):
            raise ValueError('Rating debe ser numérico')
        return float(v)

class Activity(BaseModel):
    """
    Actividad turística detallada.
    
    Attributes:
        name: Nombre de la actividad
        description: Descripción detallada
        duration: Duración en minutos
        difficulty: Nivel de dificultad
        included: Si está incluida en el precio base
        price: Precio adicional si no está incluida
        location: Ubicación de la actividad
        requirements: Requisitos especiales
        schedule: Horarios disponibles
    """
    name: str
    description: str
    duration: Optional[int] = Field(None, gt=0)
    difficulty: Optional[ActivityDifficulty] = None
    included: bool = True
    price: Optional[Decimal] = Field(None, ge=0)
    location: Optional[Location] = None
    requirements: List[str] = []
    schedule: Dict[str, List[str]] = {}

class TravelPackage(BaseModel):
    """
    Paquete turístico completo con validación avanzada.
    
    Attributes:
        id: Identificador único
        title: Título del paquete
        description: Descripción detallada
        destination: Destino principal
        price: Precio base
        currency: Moneda (ISO 4217)
        duration: Duración en días
        start_date: Fecha de inicio
        end_date: Fecha de fin
        provider: Proveedor del paquete
        status: Estado actual
        accommodation: Información de alojamiento
        activities: Lista de actividades
        included_services: Servicios incluidos
        rating: Calificación promedio
        reviews: Información de reseñas
        availability: Disponibilidad actual
        policies: Políticas aplicables
        price_history: Historial de precios
        metadata: Datos adicionales
    """
    id: str
    title: str
    description: str
    destination: str
    price: Decimal = Field(..., ge=0)
    currency: str
    duration: int = Field(..., gt=0)
    start_date: datetime
    end_date: datetime
    provider: str
    status: PackageStatus = PackageStatus.AVAILABLE
    accommodation: Accommodation
    activities: List[Activity] = []
    included_services: List[str] = []
    rating: float = Field(0.0, ge=0, le=5)
    reviews: Dict[str, Any] = {}
    availability: int = Field(0, ge=0)
    policies: Dict[str, str] = {}
    price_history: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Validar que la fecha de fin sea posterior a la de inicio."""
        if info.data.get('start_date') and v <= info.data['start_date']:
            raise ValueError('Fecha de fin debe ser posterior a fecha de inicio')
        return v

class SearchCriteria(BaseModel):
    """
    Criterios detallados de búsqueda.
    
    Attributes:
        destination: Destino deseado
        dates: Rango de fechas
        budget: Rango de presupuesto
        travelers: Información de viajeros
        preferences: Preferencias específicas
        requirements: Requisitos especiales
    """
    destination: Optional[str] = None
    dates: Dict[str, date] = {}
    budget: Dict[str, Decimal] = {}
    travelers: Dict[str, int] = {}
    preferences: Dict[str, Any] = {}
    requirements: List[str] = []

    @field_validator('budget')
    def validate_budget(cls, v):
        """Validar que el presupuesto tenga valores válidos."""
        if 'min' in v and 'max' in v and v['min'] > v['max']:
            raise ValueError('Presupuesto mínimo no puede ser mayor al máximo')
        return v

class CustomerProfile(BaseModel):
    """
    Perfil detallado del cliente.
    
    Attributes:
        id: Identificador único
        name: Nombre completo
        email: Correo electrónico
        preferences: Preferencias generales
        history: Historial de viajes
        segment: Segmento de cliente
        metrics: Métricas del cliente
    """
    id: str
    name: str
    email: str
    preferences: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []
    segment: Optional[str] = None
    metrics: Dict[str, Any] = {}

class SalesQuery(BaseModel):
    """
    Consulta detallada de venta.
    
    Attributes:
        id: Identificador único
        customer: Perfil del cliente
        criteria: Criterios de búsqueda
        priority: Nivel de prioridad
        context: Contexto de la consulta
        history: Historial de interacciones
    """
    id: str
    customer: CustomerProfile
    criteria: SearchCriteria
    priority: PriorityLevel = PriorityLevel.NORMAL
    context: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []

class AnalysisResult(BaseModel):
    """
    Resultado del análisis de cambios en paquetes.
    
    Attributes:
        package_id: ID del paquete analizado
        changes: Lista de cambios detectados
        impact_level: Nivel de impacto (0-1)
        recommendations: Recomendaciones sugeridas
        metadata: Datos adicionales del análisis
    """
    package_id: str
    changes: List[Dict[str, Any]] = []
    impact_level: float = Field(..., ge=0, le=1)
    recommendations: List[str] = []
    metadata: Dict[str, Any] = {}

    @field_validator('impact_level')
    def validate_impact(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError('Nivel de impacto debe ser numérico')
        return float(v)

def to_json(obj: Any) -> str:
    """Convertir objeto a JSON con soporte para tipos especiales."""
    def default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, Enum):
            return o.value
        return o.__dict__
    
    return json.dumps(obj, default=default)

def from_json(json_str: str, cls: type) -> Any:
    """Crear objeto desde JSON."""
    data = json.loads(json_str)
    return cls(**data)
