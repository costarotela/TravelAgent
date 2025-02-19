"""
Data schemas for travel packages and related information.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class ImpuestoLocal(BaseModel):
    """Impuestos locales específicos del destino."""
    nombre: str
    monto: str
    detalle: str

class AssistCard(BaseModel):
    """Detalles del seguro de viaje."""
    cobertura_maxima: str
    validez: str
    territorialidad: str
    limitaciones_por_edad: str
    gastos_de_reserva: float

class CotizacionEspecial(BaseModel):
    """Información de cotizaciones especiales y restricciones."""
    descripcion: str
    impuestos: List[ImpuestoLocal]
    restricciones: str

class VueloDetallado(BaseModel):
    """Información detallada de vuelos con escalas."""
    salida: str  # Incluye aeropuerto, fecha y hora (ej: "AEP 02 dom - 04:30")
    llegada: Optional[str] = None
    escala: Optional[str] = None
    espera: Optional[str] = None  # Tiempo de espera en escala
    duracion: str

class PoliticasCancelacion(BaseModel):
    """Políticas de cancelación según período."""
    periodo_0_61: str = Field(..., alias="0-61 noches antes")
    periodo_62_90: str = Field(..., alias="62-90 noches antes")
    periodo_91_plus: str = Field(..., alias="91+ noches antes")

class PoliticasCancelacionNueva(BaseModel):
    """Políticas de cancelación del paquete."""
    dias_anticipacion: int
    porcentaje_reembolso: float
    descripcion: str

class PoliticasPago(BaseModel):
    """Políticas de pago del paquete."""
    metodos_pago: List[str]
    cuotas_disponibles: List[int]
    anticipo_requerido: float
    descripcion: str

class PoliticasReembolso(BaseModel):
    """Políticas de reembolso del paquete."""
    tiempo_proceso: int
    metodos_reembolso: List[str]
    restricciones: List[str]
    descripcion: str

class VueloDetalladoNuevo(BaseModel):
    """Detalles específicos de un vuelo."""
    numero_vuelo: str
    aerolinea: str
    clase: str
    equipaje: str
    duracion: str
    escalas: List[Dict[str, Any]]

class PaqueteOLA(BaseModel):
    """Modelo completo de un paquete de viaje de OLA."""
    destino: str
    aerolinea: str
    origen: str
    duracion: int
    moneda: str
    incluye: List[str]
    fechas: List[str]
    precio: float
    impuestos: float
    politicas_cancelacion: PoliticasCancelacion
    vuelos: List[VueloDetallado]
    cotizacion_especial: Optional[CotizacionEspecial] = None
    assist_card: Optional[AssistCard] = None
    data_hash: Optional[str] = None  # Para detección de cambios

class PaqueteOLANuevo(BaseModel):
    """Paquete específico de OLA."""
    id: str
    tipo: str
    origen: str
    destino: str
    fecha_ida: datetime
    fecha_vuelta: Optional[datetime]
    precio: float
    moneda: str
    estado: str
    detalles: Dict[str, Any]
    politicas_cancelacion: Optional[PoliticasCancelacionNueva] = None
    politicas_pago: Optional[PoliticasPago] = None
    politicas_reembolso: Optional[PoliticasReembolso] = None
    vuelo: Optional[VueloDetalladoNuevo] = None

class PriceDetails(BaseModel):
    """Detalles de precio de un paquete."""
    amount: Decimal
    currency: str
    tax_included: bool = True
    tax_amount: Optional[Decimal] = None
    original_amount: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    local_taxes: Optional[List[ImpuestoLocal]] = None

class HotelDetails(BaseModel):
    """Detalles de hotel en un paquete."""
    name: str
    category: str  # e.g., "5 estrellas"
    room_type: str
    board_type: Optional[str] = None  # e.g., "All Inclusive"
    nights: Optional[int] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    location: Optional[str] = None
    amenities: Optional[List[str]] = None

class FlightDetails(BaseModel):
    """Detalles de vuelo en un paquete."""
    airline: str
    flight_number: str
    departure: str
    arrival: str
    departure_date: Optional[datetime] = None
    arrival_date: Optional[datetime] = None
    duration: Optional[str] = None
    cabin_class: Optional[str] = None
    stops: Optional[int] = None
    layovers: Optional[List[VueloDetallado]] = None

class TravelPackage(BaseModel):
    """Modelo completo de un paquete de viaje."""
    id: str
    title: str
    price_details: PriceDetails
    hotel_details: HotelDetails
    flight_details: FlightDetails
    provider: str
    last_update: datetime
    availability: Optional[int] = None
    description: Optional[str] = None
    included_services: Optional[List[str]] = None
    not_included_services: Optional[List[str]] = None
    cancellation_policy: Optional[PoliticasCancelacion] = None
    payment_options: Optional[List[str]] = None
    assist_card: Optional[AssistCard] = None
    metadata: Optional[dict] = None

class PackageSearchCriteria(BaseModel):
    """Criterios de búsqueda para paquetes."""
    origin: str
    destination: str
    date_from: datetime
    date_to: Optional[datetime] = None
    passengers: int = 2
    flexible_dates: bool = False
    max_price: Optional[Decimal] = None
    min_category: Optional[int] = None  # Categoría mínima del hotel
    board_types: Optional[List[str]] = None  # Tipos de pensión aceptados
    airlines: Optional[List[str]] = None  # Aerolíneas preferidas

class CustomerProfile(BaseModel):
    """Perfil del cliente con preferencias y datos de contacto."""
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    travel_history: Optional[List[str]] = None
    budget_range: Optional[Dict[str, Decimal]] = None
    preferred_destinations: Optional[List[str]] = None
    preferred_airlines: Optional[List[str]] = None
    preferred_accommodations: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class CustomerProfileNuevo(BaseModel):
    """Perfil del cliente."""
    id: str
    nombre: str
    email: str
    telefono: str
    preferencias: Dict[str, Any]

class SearchCriteria(BaseModel):
    """Criterios de búsqueda para paquetes."""
    destination: str
    date_from: datetime
    date_to: Optional[datetime] = None
    adults: int = 2
    children: Optional[int] = 0
    budget_max: Optional[Decimal] = None
    preferred_airlines: Optional[List[str]] = None
    accommodation_type: Optional[List[str]] = None
    board_type: Optional[List[str]] = None
    flexible_dates: bool = False

class SearchCriteriaNuevo(BaseModel):
    """Criterios de búsqueda."""
    origen: str
    destino: str
    fecha_ida: datetime
    fecha_vuelta: Optional[datetime] = None
    pasajeros: Dict[str, int] = None
    clase: str = "Economy"
    precio_maximo: Optional[float] = None

class Accommodation(BaseModel):
    """Detalles de alojamiento."""
    id: str
    name: str
    type: str
    category: int
    location: str
    amenities: List[str]
    room_types: List[str]
    board_types: List[str]
    price_range: Dict[str, Decimal]

class AccommodationType(BaseModel):
    """Tipo de alojamiento."""
    id: str
    name: str
    description: str
    features: List[str]
    category_range: List[int]

class AccommodationTypeNuevo(BaseModel):
    """Tipo de alojamiento."""
    id: str
    nombre: str
    categoria: str
    descripcion: str
    amenities: List[str]

class Activity(BaseModel):
    """Actividades disponibles en el destino."""
    id: str
    name: str
    description: str
    duration: str
    price: Decimal
    location: str
    included: bool = False
    availability: Dict[str, List[datetime]]

class Location(BaseModel):
    """Información de ubicación."""
    id: str
    name: str
    country: str
    region: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    timezone: Optional[str] = None
    description: Optional[str] = None

class PackageStatus(BaseModel):
    """Estado actual del paquete."""
    id: str
    availability: int
    last_update: datetime
    price_history: List[Dict[str, Any]]
    status: str
    changes_detected: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]

class PackageStatusNuevo(BaseModel):
    """Estado de un paquete."""
    id: str
    estado: str
    ultima_actualizacion: datetime
    historial: List[Dict[str, Any]]

class AnalysisResult(BaseModel):
    """Resultado del análisis de cambios en un paquete."""
    package_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    changes_detected: Dict[str, Any]
    impact_score: float  # 0.0 a 1.0
    severity: str  # "low", "medium", "high"
    affected_components: List[str]
    recommendations: List[Dict[str, Any]]
    alternatives: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    requires_action: bool = False
    action_deadline: Optional[datetime] = None
    notes: Optional[str] = None

class AnalysisResultNuevo(BaseModel):
    """Resultado de análisis de paquete."""
    id: str
    score: float
    recomendaciones: List[str]
    alertas: List[str]
    detalles: Dict[str, Any]

class SalesQuery(BaseModel):
    """Consulta de ventas y métricas."""
    date_from: datetime
    date_to: Optional[datetime] = None
    customer_id: Optional[str] = None
    package_id: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    metrics: List[str] = Field(default_factory=list)  # e.g. ["revenue", "margin", "conversion_rate"]
    group_by: Optional[List[str]] = None  # e.g. ["provider", "destination"]
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "desc"
    limit: Optional[int] = None

class SalesQueryNuevo(BaseModel):
    """Consulta de ventas."""
    vendor_id: str
    fecha_inicio: datetime
    fecha_fin: datetime
    filtros: Optional[Dict[str, Any]] = None
