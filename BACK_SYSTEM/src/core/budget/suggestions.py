"""Motor de sugerencias para presupuestos."""

from typing import Dict, List
from datetime import datetime, timedelta
from decimal import Decimal

from src.core.budget.models import Budget
from src.core.providers.base import TravelPackage
from src.utils.database import Database


class SuggestionEngine:
    """Motor de sugerencias para presupuestos."""

    def __init__(self):
        """Inicializar motor de sugerencias."""
        self.db = Database()

    def get_suggestions(self, budget: Budget) -> Dict[str, List[str]]:
        """Obtener sugerencias para un presupuesto."""
        suggestions = {
            "optimizations": [],
            "warnings": [],
            "opportunities": []
        }

        # Analizar precios
        self._analyze_prices(budget, suggestions)

        # Analizar temporada
        self._analyze_seasonality(budget, suggestions)

        # Analizar disponibilidad
        self._analyze_availability(budget, suggestions)

        # Analizar alternativas
        self._find_alternatives(budget, suggestions)

        return suggestions

    def _analyze_prices(self, budget: Budget, suggestions: Dict[str, List[str]]):
        """Analizar precios y sugerir optimizaciones."""
        for item in budget.items:
            # Comparar con precios históricos
            avg_price = self._get_average_price(item.type, item.description)
            if avg_price and item.unit_price > avg_price * Decimal('1.15'):
                suggestions["warnings"].append(
                    f"El precio para {item.description} está 15% por encima del promedio histórico"
                )
                suggestions["optimizations"].append(
                    f"Considerar negociar el precio de {item.description}"
                )

    def _analyze_seasonality(self, budget: Budget, suggestions: Dict[str, List[str]]):
        """Analizar temporada y sugerir ajustes."""
        for item in budget.items:
            if "departure_date" in item.details:
                departure = item.details["departure_date"]
                
                # Verificar temporada alta
                if self._is_high_season(departure):
                    suggestions["warnings"].append(
                        f"Viaje programado en temporada alta. Precios pueden ser más elevados."
                    )
                    suggestions["optimizations"].append(
                        "Considerar fechas alternativas para mejor precio"
                    )

                # Verificar anticipación
                if departure - datetime.now() < timedelta(days=30):
                    suggestions["warnings"].append(
                        "Reserva con poca anticipación. Precios pueden ser más altos."
                    )

    def _analyze_availability(self, budget: Budget, suggestions: Dict[str, List[str]]):
        """Analizar disponibilidad y sugerir alternativas."""
        for item in budget.items:
            availability = self._check_availability(item.type, item.description)
            if availability and availability < 5:
                suggestions["warnings"].append(
                    f"¡Pocas plazas disponibles para {item.description}!"
                )
                suggestions["optimizations"].append(
                    "Considerar asegurar la reserva pronto"
                )

    def _find_alternatives(self, budget: Budget, suggestions: Dict[str, List[str]]):
        """Encontrar alternativas para los items del presupuesto."""
        for item in budget.items:
            alternatives = self._get_alternatives(item)
            if alternatives:
                key = f"alternatives_{item.id}"
                suggestions[key] = []
                
                for alt in alternatives:
                    if alt.price < item.unit_price:
                        savings = item.unit_price - alt.price
                        suggestions[key].append({
                            "id": alt.id,
                            "description": alt.description,
                            "price": float(alt.price),
                            "currency": alt.currency,
                            "potential_savings": float(savings)
                        })
                        
                        if len(suggestions[key]) >= 3:  # Limitar a 3 alternativas
                            break

    def _get_average_price(self, item_type: str, description: str) -> Optional[Decimal]:
        """Obtener precio promedio histórico."""
        # TODO: Implementar lógica real de consulta
        return Decimal('1000.00')

    def _is_high_season(self, date: datetime) -> bool:
        """Determinar si una fecha está en temporada alta."""
        # TODO: Implementar lógica real de temporada alta
        month = date.month
        return month in [1, 2, 7, 12]  # Temporada alta en verano y vacaciones

    def _check_availability(self, item_type: str, description: str) -> Optional[int]:
        """Verificar disponibilidad actual."""
        # TODO: Implementar lógica real de consulta
        return 10

    def _get_alternatives(self, item) -> List[TravelPackage]:
        """Obtener alternativas para un ítem."""
        # TODO: Implementar lógica real de búsqueda
        return []
