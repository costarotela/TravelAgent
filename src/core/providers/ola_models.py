"""Modelos de datos para el proveedor OLA."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Vuelo(BaseModel):
    """Modelo para información de vuelos."""

    salida: str = Field(..., description="Hora de salida del vuelo")
    llegada: Optional[str] = Field(None, description="Hora de llegada del vuelo")
    escala: Optional[str] = Field(None, description="Lugar de escala si existe")
    espera: Optional[str] = Field(None, description="Tiempo de espera en escala")
    duracion: str = Field(..., description="Duración total del vuelo")
    numero_vuelo: Optional[str] = Field(None, description="Número de vuelo")
    aerolinea: str = Field(..., description="Nombre de la aerolínea")


class ImpuestoEspecial(BaseModel):
    """Modelo para impuestos especiales."""

    nombre: str = Field(..., description="Nombre del impuesto")
    monto: float = Field(..., description="Monto del impuesto")
    detalle: str = Field(..., description="Detalles adicionales")


class PoliticasCancelacion(BaseModel):
    """Modelo para políticas de cancelación."""

    periodo_61_noches: str = Field(
        ...,
        alias="0-61 noches antes",
        description="Política para cancelaciones entre 0 y 61 noches antes",
    )
    periodo_62_90: str = Field(
        ...,
        alias="62-90 noches antes",
        description="Política para cancelaciones entre 62 y 90 noches antes",
    )
    periodo_91_plus: str = Field(
        ...,
        alias="91+ noches antes",
        description="Política para cancelaciones de 91 noches o más antes",
    )


class PaqueteOLA(BaseModel):
    """Modelo para paquetes turísticos de OLA."""

    # Identificador
    id: str = Field(..., description="Identificador único del paquete")

    # Información básica
    destino: str = Field(..., description="Destino del viaje")
    origen: str = Field(..., description="Origen del viaje")
    duracion: int = Field(..., description="Duración en días")

    # Información de vuelos
    vuelos: List[Vuelo] = Field(..., description="Lista de vuelos incluidos")
    aerolinea: str = Field(..., description="Aerolínea principal")

    # Información económica
    moneda: str = Field(..., description="Moneda del precio")
    precio: float = Field(..., description="Precio base del paquete")
    precio_anterior: Optional[float] = Field(
        None, description="Precio anterior para tracking de cambios"
    )
    impuestos: float = Field(..., description="Impuestos base")
    impuestos_especiales: Optional[List[ImpuestoEspecial]] = Field(
        None, description="Lista de impuestos especiales"
    )

    # Fechas y disponibilidad
    fechas: List[datetime] = Field(..., description="Fechas disponibles")
    disponibilidad: bool = Field(True, description="Disponibilidad actual")
    disponibilidad_anterior: Optional[bool] = Field(
        None, description="Disponibilidad anterior para tracking de cambios"
    )

    # Detalles adicionales
    incluye: List[str] = Field(..., description="Servicios incluidos")
    politicas_cancelacion: PoliticasCancelacion = Field(
        ..., description="Políticas de cancelación"
    )
    cotizacion_especial: Optional[Dict[str, List[ImpuestoEspecial]]] = Field(
        None, description="Cotización especial"
    )
    assist_card: Optional[Dict] = Field(None, description="Detalles de Assist Card")
    restricciones: Optional[str] = Field(None, description="Restricciones especiales")

    # Campo para tracking de cambios
    data_hash: Optional[str] = Field(None, description="Hash para detectar cambios")

    class Config:
        """Configuración del modelo."""

        json_encoders = {datetime: lambda v: v.strftime("%Y-%m-%d")}
