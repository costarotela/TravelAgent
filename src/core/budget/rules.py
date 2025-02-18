"""Basic budget rules."""

from typing import Dict, Optional
from src.core.models.travel import TravelPackage


class BudgetRules:
    """Simple rules for budget creation and validation."""

    def __init__(self):
        """Initialize budget rules with basic margins."""
        self.base_margins = {
            "regular": 0.15,    # 15% margen regular
            "corporate": 0.10,  # 10% margen corporativo
            "vip": 0.20        # 20% margen VIP
        }

    def apply_margin(self, price: float, client_type: str = "regular") -> float:
        """Apply margin based on client type.

        Args:
            price: Base price
            client_type: Type of client (regular, corporate, vip)

        Returns:
            Price with margin applied
        """
        margin = self.base_margins.get(client_type.lower(), 0.15)
        return price * (1 + margin)

    def check_availability(self, package: TravelPackage) -> bool:
        """Check if package is available for budget.

        Args:
            package: Package to check

        Returns:
            True if package is available
        """
        if not hasattr(package, "availability"):
            return True
        return bool(package.availability)

    def validate_budget_items(self, items: Dict) -> Dict[str, str]:
        """Basic validation of budget items.

        Args:
            items: Budget items to validate

        Returns:
            Dictionary of validation errors, empty if valid
        """
        errors = {}

        for key, item in items.items():
            # Validar precio
            if item.get("price", 0) <= 0:
                errors[key] = "Precio debe ser mayor a 0"

            # Validar fechas
            if not item.get("date"):
                errors[key] = "Fecha es requerida"

            # Validar proveedor
            if not item.get("provider"):
                errors[key] = "Proveedor es requerido"

        return errors

    def adjust_price_for_season(
        self,
        price: float,
        date: str,
        service_type: str
    ) -> float:
        """Simple seasonal price adjustment.

        Args:
            price: Base price
            date: Service date
            service_type: Type of service

        Returns:
            Adjusted price
        """
        # Ajustes básicos por temporada
        season_multipliers = {
            "high": 1.2,    # Temporada alta
            "medium": 1.1,  # Temporada media
            "low": 1.0      # Temporada baja
        }

        # Determinar temporada (implementación simple)
        season = self._determine_season(date, service_type)
        multiplier = season_multipliers.get(season, 1.0)

        return price * multiplier

    def _determine_season(self, date: str, service_type: str) -> str:
        """Simple season determination.
        
        This is a basic implementation that could be expanded based on
        actual business rules.
        """
        # Por ahora retorna temporada baja por defecto
        return "low"
