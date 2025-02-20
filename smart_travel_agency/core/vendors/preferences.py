"""
Sistema de preferencias para vendedores.

Este módulo implementa un sistema de preferencias en tres niveles que permite:

1. Nivel Base (Proveedores):
   - Filtros básicos como aerolíneas y ratings
   - Configuraciones estándar de búsqueda
   - Exclusiones de proveedores

2. Nivel Negocio (Empresa):
   - Reglas de margen y comisiones
   - Perfiles predefinidos de clientes
   - Ajustes estacionales y promociones
   - Políticas de pago y financiación

3. Nivel Vendedor (Personal):
   - Combinaciones exitosas de paquetes
   - Notas y observaciones por destino
   - Métricas de rendimiento personal
   - Preferencias de búsqueda individuales

El sistema está diseñado para:
- Optimizar resultados de búsqueda
- Facilitar la construcción de presupuestos
- Mantener un historial de éxitos
- Permitir la reconstrucción de presupuestos
- Adaptarse a diferentes perfiles de cliente

Ejemplo de uso:
    >>> # Crear preferencias base
    >>> base_prefs = BasePreferences(
    ...     preferred_airlines=["LATAM", "AA"],
    ...     min_rating=4.0
    ... )
    >>> 
    >>> # Crear preferencias de vendedor
    >>> vendor_prefs = VendorPreferences(
    ...     vendor_id="V001",
    ...     name="Juan Pérez",
    ...     base=base_prefs
    ... )
    >>> 
    >>> # Actualizar en el gestor
    >>> manager = PreferenceManager()
    >>> manager.update_vendor_preferences(vendor_prefs)
    >>> 
    >>> # Aplicar a paquetes
    >>> filtered = manager.apply_preferences(packages, "V001")
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union
from enum import Enum


class ClientType(Enum):
    """
    Tipos de cliente soportados.
    
    Attributes:
        INDIVIDUAL: Viajero individual
        FAMILY: Grupo familiar
        BUSINESS: Viaje de negocios
        GROUP: Grupo organizado
        HONEYMOON: Luna de miel
    """
    
    INDIVIDUAL = "individual"
    FAMILY = "family"
    BUSINESS = "business"
    GROUP = "group"
    HONEYMOON = "honeymoon"


class PackageType(Enum):
    """
    Tipos de paquete según nivel de servicio.
    
    Attributes:
        ECONOMIC: Paquete económico
        STANDARD: Paquete estándar
        PREMIUM: Paquete premium
        LUXURY: Paquete de lujo
    """
    
    ECONOMIC = "economic"
    STANDARD = "standard"
    PREMIUM = "premium"
    LUXURY = "luxury"


@dataclass
class ClientProfile:
    """
    Perfil de cliente con preferencias específicas.
    
    Este perfil ayuda a personalizar las búsquedas y
    recomendaciones según el tipo de cliente.
    
    Attributes:
        client_type: Tipo de cliente
        typical_budget: Presupuesto típico
        preferred_destinations: Destinos preferidos
        typical_stay_length: Duración típica de estadía
        preferred_activities: Actividades preferidas
        dietary_restrictions: Restricciones alimentarias
        accessibility_needs: Necesidades de accesibilidad
        notes: Notas adicionales
    """
    
    client_type: ClientType
    typical_budget: Decimal
    preferred_destinations: List[str]
    typical_stay_length: int
    preferred_activities: List[str]
    dietary_restrictions: List[str] = field(default_factory=list)
    accessibility_needs: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class PriceRule:
    """
    Regla para ajuste automático de precios.
    
    Las reglas se evalúan en orden de prioridad y pueden
    modificar el precio final del paquete.
    
    Attributes:
        condition: Expresión evaluable (ej: "package.total_price > 1000")
        adjustment: Valor fijo o fórmula de ajuste
        priority: Prioridad de la regla (mayor = más prioritaria)
        description: Descripción de la regla
    """
    
    condition: str
    adjustment: Union[Decimal, str]
    priority: int
    description: str


@dataclass
class PackageRule:
    """
    Regla para composición de paquetes.
    
    Define restricciones y requisitos para la
    construcción de paquetes válidos.
    
    Attributes:
        condition: Condición de aplicación
        required_components: Componentes requeridos
        forbidden_components: Componentes prohibidos
        priority: Prioridad de la regla
        description: Descripción de la regla
    """
    
    condition: str
    required_components: List[str]
    forbidden_components: List[str]
    priority: int
    description: str


@dataclass
class PackageCombination:
    """
    Combinación exitosa de componentes de paquete.
    
    Registra combinaciones que han tenido éxito en
    ventas anteriores para su reutilización.
    
    Attributes:
        origin: Ciudad de origen
        destination: Ciudad de destino
        flight_pattern: Patrón de vuelos
        hotel_category: Categoría de hotel
        activities: Lista de actividades
        success_rate: Tasa de éxito
        total_sales: Total de ventas
        last_used: Última vez utilizado
        notes: Notas adicionales
    """
    
    origin: str
    destination: str
    flight_pattern: str
    hotel_category: str
    activities: List[str]
    success_rate: float
    total_sales: int
    last_used: datetime
    notes: str = ""


@dataclass
class BasePreferences:
    """
    Preferencias básicas a nivel proveedor.
    
    Define filtros básicos que se aplican directamente
    en las búsquedas con proveedores.
    
    Attributes:
        preferred_airlines: Aerolíneas preferidas
        min_rating: Rating mínimo aceptable
        max_price: Precio máximo (opcional)
        room_types: Tipos de habitación aceptables
        meal_plans: Planes de comida aceptables
        excluded_providers: Proveedores excluidos
    """
    
    preferred_airlines: List[str] = field(default_factory=list)
    min_rating: float = 0.0
    max_price: Optional[Decimal] = None
    room_types: List[str] = field(default_factory=list)
    meal_plans: List[str] = field(default_factory=list)
    excluded_providers: List[str] = field(default_factory=list)


@dataclass
class BusinessPreferences:
    """
    Preferencias a nivel empresa.
    
    Define reglas y políticas generales de la
    agencia de viajes.
    
    Attributes:
        default_margin: Margen predeterminado
        min_margin: Margen mínimo aceptable
        max_margin: Margen máximo permitido
        commission_rate: Tasa de comisión
        payment_methods: Métodos de pago aceptados
        installment_options: Opciones de cuotas
        client_profiles: Perfiles predefinidos
        seasonal_adjustments: Ajustes por temporada
        price_rules: Reglas de precio
        package_rules: Reglas de paquetes
    """
    
    default_margin: Decimal = Decimal("0.15")
    min_margin: Decimal = Decimal("0.05")
    max_margin: Decimal = Decimal("0.35")
    commission_rate: Decimal = Decimal("0.10")
    payment_methods: List[str] = field(default_factory=list)
    installment_options: List[int] = field(default_factory=list)
    client_profiles: Dict[str, ClientProfile] = field(default_factory=dict)
    seasonal_adjustments: Dict[str, float] = field(default_factory=dict)
    price_rules: List[PriceRule] = field(default_factory=list)
    package_rules: List[PackageRule] = field(default_factory=list)


@dataclass
class VendorPreferences:
    """
    Preferencias personalizadas del vendedor.
    
    Captura la experiencia y preferencias individuales
    de cada vendedor.
    
    Attributes:
        vendor_id: ID único del vendedor
        name: Nombre del vendedor
        base: Preferencias base
        successful_combinations: Combinaciones exitosas
        success_rate_threshold: Umbral de éxito
        price_variation_threshold: Variación máxima de precio
        destination_notes: Notas por destino
        provider_notes: Notas por proveedor
        general_notes: Notas generales
        last_updated: Última actualización
        created_at: Fecha de creación
    """
    
    vendor_id: str
    name: str
    base: BasePreferences = field(default_factory=BasePreferences)
    successful_combinations: List[PackageCombination] = field(default_factory=list)
    success_rate_threshold: float = 0.7
    price_variation_threshold: float = 0.15
    destination_notes: Dict[str, str] = field(default_factory=dict)
    provider_notes: Dict[str, str] = field(default_factory=dict)
    general_notes: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)


class PreferenceManager:
    """
    Gestor central de preferencias.
    
    Coordina la aplicación de preferencias en todos los
    niveles y mantiene el estado global.
    
    Methods:
        get_vendor_preferences: Obtiene preferencias de vendedor
        update_vendor_preferences: Actualiza preferencias
        apply_preferences: Aplica preferencias a paquetes
    """
    
    def __init__(self):
        """Inicializa el gestor con configuración predeterminada."""
        self.business_preferences = BusinessPreferences()
        self.vendor_preferences: Dict[str, VendorPreferences] = {}
        
    def get_vendor_preferences(self, vendor_id: str) -> Optional[VendorPreferences]:
        """
        Obtiene las preferencias de un vendedor.
        
        Args:
            vendor_id: ID del vendedor
            
        Returns:
            Preferencias del vendedor o None si no existe
        """
        return self.vendor_preferences.get(vendor_id)
    
    def update_vendor_preferences(self, preferences: VendorPreferences) -> None:
        """
        Actualiza las preferencias de un vendedor.
        
        Args:
            preferences: Nuevas preferencias
        """
        preferences.last_updated = datetime.now()
        self.vendor_preferences[preferences.vendor_id] = preferences
    
    def apply_preferences(
        self,
        packages: List["TravelPackage"],
        vendor_id: str
    ) -> List["TravelPackage"]:
        """
        Aplica las preferencias a una lista de paquetes.
        
        Args:
            packages: Lista de paquetes a filtrar
            vendor_id: ID del vendedor
            
        Returns:
            Lista filtrada de paquetes
        """
        vendor_prefs = self.get_vendor_preferences(vendor_id)
        if not vendor_prefs:
            return packages
            
        filtered_packages = []
        for package in packages:
            if self._package_matches_preferences(package, vendor_prefs):
                filtered_packages.append(package)
                
        return filtered_packages
    
    def _package_matches_preferences(
        self,
        package: "TravelPackage",
        preferences: VendorPreferences
    ) -> bool:
        """
        Verifica si un paquete cumple con las preferencias.
        
        Args:
            package: Paquete a verificar
            preferences: Preferencias a aplicar
            
        Returns:
            True si el paquete cumple las preferencias
        """
        # Verificar aerolíneas
        if preferences.base.preferred_airlines:
            if not any(
                flight.airline in preferences.base.preferred_airlines
                for flight in package.flights
            ):
                return False
                
        # Verificar precio máximo
        if (preferences.base.max_price and
            package.total_price > preferences.base.max_price):
            return False
            
        # Verificar rating mínimo
        if (preferences.base.min_rating and
            package.accommodation and
            package.accommodation.rating < preferences.base.min_rating):
            return False
            
        # Verificar proveedor excluido
        if package.provider_id in preferences.base.excluded_providers:
            return False
            
        return True


# Instancia global
preference_manager = PreferenceManager()


def get_preference_manager() -> PreferenceManager:
    """
    Obtiene la instancia global del gestor de preferencias.
    
    Returns:
        Instancia única del gestor
    """
    return preference_manager
