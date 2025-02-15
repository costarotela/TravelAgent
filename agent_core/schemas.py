"""
Modelos de datos centrales del agente de viajes.
Implementa validación avanzada y documentación detallada.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import json
from pydantic import BaseModel, validator, Field
from pydantic.dataclasses import dataclass as pydantic_dataclass

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

@pydantic_dataclass
class Location:
    """
    Información detallada de ubicación.
    
    Attributes:
        latitude: Latitud en grados decimales
        longitude: Longitud en grados decimales
        address: Dirección física completa
        city: Ciudad
        country: País
        postal_code: Código postal
    """
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str
    city: str
    country: str
    postal_code: Optional[str] = None
    
    @validator('latitude', 'longitude')
    def validate_coordinates(cls, v):
        """Validar que las coordenadas sean números válidos."""
        if not isinstance(v, (int, float)):
            raise ValueError('Coordenada debe ser numérica')
        return float(v)

@pydantic_dataclass
class Accommodation:
    """
    Información detallada de alojamiento.
    
    Attributes:
        name: Nombre del alojamiento
        type: Tipo de alojamiento
        rating: Calificación (0-5)
        stars: Categoría en estrellas (0-5)
        amenities: Lista de comodidades
        room_types: Tipos de habitación disponibles
        location: Información de ubicación
        images: URLs de imágenes
        description: Descripción detallada
        policies: Políticas del alojamiento
    """
    name: str
    type: AccommodationType
    rating: float = Field(..., ge=0, le=5)
    stars: int = Field(..., ge=0, le=5)
    amenities: List[str] = field(default_factory=list)
    room_types: List[str] = field(default_factory=list)
    location: Location
    images: List[str] = field(default_factory=list)
    description: Optional[str] = None
    policies: Dict[str, str] = field(default_factory=dict)
    
    @validator('rating')
    def validate_rating(cls, v):
        """Validar que el rating sea un número válido."""
        if not isinstance(v, (int, float)):
            raise ValueError('Rating debe ser numérico')
        return float(v)

@pydantic_dataclass
class Activity:
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
    requirements: List[str] = field(default_factory=list)
    schedule: Dict[str, List[str]] = field(default_factory=dict)

@pydantic_dataclass
class TravelPackage:
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
    activities: List[Activity] = field(default_factory=list)
    included_services: List[str] = field(default_factory=list)
    rating: float = Field(0.0, ge=0, le=5)
    reviews: Dict[str, Any] = field(default_factory=dict)
    availability: int = Field(0, ge=0)
    policies: Dict[str, str] = field(default_factory=dict)
    price_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        """Validar que la fecha de fin sea posterior a la de inicio."""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('La fecha de fin debe ser posterior a la de inicio')
        return v

@pydantic_dataclass
class SearchCriteria:
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
    dates: Dict[str, date] = field(default_factory=dict)
    budget: Dict[str, Decimal] = field(default_factory=dict)
    travelers: Dict[str, int] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    requirements: List[str] = field(default_factory=list)
    
    @validator('budget')
    def validate_budget(cls, v):
        """Validar que el presupuesto tenga valores válidos."""
        if 'min' in v and 'max' in v and v['min'] > v['max']:
            raise ValueError('El presupuesto mínimo no puede ser mayor al máximo')
        return v

@pydantic_dataclass
class CustomerProfile:
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
    preferences: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    segment: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

@pydantic_dataclass
class SalesQuery:
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
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

# Más modelos según necesidad...

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
