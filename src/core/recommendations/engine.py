"""Price and supplier analysis engine implementation."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from prophet import Prophet
from prometheus_client import Counter, Histogram

from .models import (
    PriceTrend,
    ConfidenceLevel,
    PriceAnalysis,
    SupplierMetrics,
    SupplierAnalysis,
    AnalysisContext,
)
from ..monitoring import METRICS

logger = logging.getLogger(__name__)

# Initialize metrics
METRICS["analysis_operations"] = Counter(
    "analysis_operations_total",
    "Total number of analysis operations",
    ["analysis_type"],
)
METRICS["analysis_processing_time"] = Histogram(
    "analysis_processing_seconds",
    "Time taken to process analysis",
)


class AnalysisEngine:
    """Engine for price and supplier analysis."""

    def __init__(self, model_path: Optional[str] = None):
        """Initialize analysis engine.

        Args:
            model_path: Optional path to pre-trained models
        """
        self.model_path = model_path
        self.price_model = Prophet()
        self._load_models()

    def _load_models(self) -> None:
        """Load pre-trained models."""
        # TODO: Implement model loading
        pass

    async def analyze_price(self, context: AnalysisContext) -> PriceAnalysis:
        """Analyze price trends and variations.

        Args:
            context: Analysis context

        Returns:
            Price analysis
        """
        start_time = datetime.utcnow()

        try:
            # Preparar datos
            df = self._prepare_price_data(context.historical_prices)

            # Entrenar modelo
            self.price_model.fit(df)

            # Hacer predicciones
            future = self.price_model.make_future_dataframe(periods=30)
            forecast = self.price_model.predict(future)

            # Analizar tendencias
            trend = self._analyze_price_trend(forecast)
            variation = self._calculate_expected_variation(
                forecast, context.package_data["price"]
            )

            # Determinar confianza
            confidence = self._calculate_confidence(forecast, context.historical_prices)

            analysis = PriceAnalysis(
                item_id=context.package_data["id"],
                current_price=context.package_data["price"],
                historical_prices=context.historical_prices,
                trend=trend,
                confidence=confidence,
                expected_variation=variation,
                factors=self._get_trend_factors(forecast),
            )

            # Update metrics
            METRICS["analysis_operations"].labels(analysis_type="price").inc()

            return analysis

        finally:
            # Record processing time
            duration = (datetime.utcnow() - start_time).total_seconds()
            METRICS["analysis_processing_time"].observe(duration)

    async def analyze_supplier(
        self,
        context: AnalysisContext,
        supplier_id: str,
    ) -> SupplierAnalysis:
        """Analyze supplier performance and metrics.

        Args:
            context: Analysis context
            supplier_id: ID of supplier to analyze

        Returns:
            Supplier analysis
        """
        start_time = datetime.utcnow()

        try:
            # Obtener datos del proveedor
            supplier_data = self._get_supplier_data(supplier_id, context.supplier_data)
            if not supplier_data:
                raise ValueError(f"Supplier {supplier_id} not found")

            # Calcular métricas
            metrics = self._calculate_supplier_metrics(
                supplier_data,
                supplier_data["service_type"],
                context.market_data,
            )

            # Analizar rendimiento histórico
            history = self._analyze_historical_performance(
                supplier_data, context.market_data
            )

            # Generar recomendaciones
            recommendations = self._generate_supplier_recommendations(metrics, history)

            # Determinar confianza
            confidence = self._calculate_supplier_confidence(metrics, history)

            analysis = SupplierAnalysis(
                supplier_id=supplier_id,
                service_type=supplier_data["service_type"],
                metrics=metrics,
                historical_performance=history,
                confidence=confidence,
                recommendations=recommendations,
            )

            # Update metrics
            METRICS["analysis_operations"].labels(analysis_type="supplier").inc()

            return analysis

        finally:
            # Record processing time
            duration = (datetime.utcnow() - start_time).total_seconds()
            METRICS["analysis_processing_time"].observe(duration)

    def _prepare_price_data(
        self, historical_prices: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Prepare historical price data for analysis."""
        # Convertir a DataFrame
        df = pd.DataFrame(historical_prices)

        # Asegurar formato correcto para Prophet
        df = df.rename(columns={"timestamp": "ds", "price": "y"})

        # Ordenar por fecha
        df = df.sort_values("ds")

        # Agregar features adicionales
        df["is_weekend"] = df["ds"].dt.dayofweek.isin([5, 6])
        df["month"] = df["ds"].dt.month
        df["day_of_week"] = df["ds"].dt.dayofweek

        return df

    def _analyze_price_trend(self, forecast: pd.DataFrame) -> PriceTrend:
        """Analyze price trend from forecast."""
        # Calcular cambio porcentual
        total_change = (
            (forecast["yhat"].iloc[-1] - forecast["yhat"].iloc[0])
            / forecast["yhat"].iloc[0]
            * 100
        )

        # Calcular volatilidad
        volatility = forecast["yhat"].std() / forecast["yhat"].mean()

        # Determinar tendencia
        if volatility > 0.15:  # Más de 15% de volatilidad
            return PriceTrend.VOLATILE
        elif total_change > 5:  # Más de 5% de aumento
            return PriceTrend.INCREASING
        elif total_change < -5:  # Más de 5% de disminución
            return PriceTrend.DECREASING
        else:
            return PriceTrend.STABLE

    def _calculate_expected_variation(
        self, forecast: pd.DataFrame, current_price: float
    ) -> float:
        """Calculate expected price variation."""
        # Calcular variación esperada
        future_price = forecast["yhat"].iloc[-1]
        variation = ((future_price - current_price) / current_price) * 100
        return variation

    def _calculate_confidence(
        self,
        forecast: pd.DataFrame,
        historical_data: List[Dict[str, Any]],
    ) -> ConfidenceLevel:
        """Calculate confidence level."""
        # Calcular error medio
        mape = np.mean(np.abs(forecast["yhat"] - forecast["y"]) / forecast["y"]) * 100

        # Calcular R²
        r2 = 1 - (
            np.sum((forecast["y"] - forecast["yhat"]) ** 2)
            / np.sum((forecast["y"] - forecast["y"].mean()) ** 2)
        )

        # Determinar nivel de confianza
        if mape < 10 and r2 > 0.8:
            return ConfidenceLevel.HIGH
        elif mape < 20 and r2 > 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _get_trend_factors(self, forecast: pd.DataFrame) -> List[str]:
        """Get factors influencing trend."""
        factors = []

        # Analizar componentes de la predicción
        components = ["trend", "weekly", "yearly"]

        for component in components:
            # Calcular importancia del componente
            importance = np.std(forecast[component]) / np.std(forecast["yhat"])

            if importance > 0.1:  # Más de 10% de importancia
                if component == "trend":
                    factors.append("tendencia_general")
                elif component == "weekly":
                    factors.append("patron_semanal")
                elif component == "yearly":
                    factors.append("estacionalidad")

        # Analizar eventos especiales
        if "holidays" in forecast.columns:
            holiday_effect = np.std(forecast["holidays"]) / np.std(forecast["yhat"])
            if holiday_effect > 0.05:
                factors.append("eventos_especiales")

        return factors

    def _get_supplier_data(
        self,
        supplier_id: str,
        supplier_data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Get supplier data by ID."""
        if not supplier_data:
            return None

        suppliers = supplier_data.get("suppliers", [])
        for supplier in suppliers:
            if supplier["id"] == supplier_id:
                return supplier

        return None

    def _calculate_supplier_metrics(
        self,
        supplier: Dict[str, Any],
        service_type: str,
        market_data: Dict[str, Any],
    ) -> SupplierMetrics:
        """Calculate metrics for a supplier."""
        # Calcular métricas base
        reliability = self._calculate_reliability_score(supplier)
        competitiveness = self._calculate_price_competitiveness(
            supplier, service_type, market_data
        )
        quality = supplier.get("rating", 0) / 5.0
        response_time = self._calculate_response_time(supplier)

        return SupplierMetrics(
            reliability_score=reliability,
            price_competitiveness=competitiveness,
            service_quality=quality,
            response_time=response_time,
        )

    def _calculate_reliability_score(self, supplier: Dict[str, Any]) -> float:
        """Calculate supplier reliability score."""
        # Factores de confiabilidad
        factors = {
            "on_time_delivery": supplier.get("on_time_delivery", 0),
            "cancellation_rate": 1 - supplier.get("cancellation_rate", 0),
            "response_rate": supplier.get("response_rate", 0),
        }

        # Pesos de los factores
        weights = {
            "on_time_delivery": 0.4,
            "cancellation_rate": 0.4,
            "response_rate": 0.2,
        }

        # Calcular score ponderado
        score = sum(factors[k] * weights[k] for k in factors.keys())

        return max(0, min(1, score))  # Normalizar a [0,1]

    def _calculate_price_competitiveness(
        self,
        supplier: Dict[str, Any],
        service_type: str,
        market_data: Dict[str, Any],
    ) -> float:
        """Calculate price competitiveness score."""
        if not market_data:
            return 0.5

        # Obtener precios del mercado
        market_prices = [
            s["price"] for s in market_data.get("services", {}).get(service_type, [])
        ]

        if not market_prices:
            return 0.5

        # Calcular posición relativa
        avg_price = np.mean(market_prices)
        if avg_price == 0:
            return 0.5

        ratio = supplier["price"] / avg_price

        # Convertir ratio a score (menor precio = mejor score)
        score = 1 - min(1, max(0, ratio - 0.5))

        return score

    def _calculate_response_time(self, supplier: Dict[str, Any]) -> float:
        """Calculate average response time in hours."""
        response_times = supplier.get("response_times", [])
        if not response_times:
            return 24.0  # Valor por defecto

        return np.mean(response_times)

    def _analyze_historical_performance(
        self,
        supplier: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Analyze historical performance."""
        history = []

        # Obtener historial
        performance = supplier.get("performance_history", [])

        for entry in performance:
            analysis = {
                "timestamp": entry["timestamp"],
                "metrics": {
                    "reliability": self._calculate_reliability_score(
                        {
                            **supplier,
                            **entry,
                        }
                    ),
                    "competitiveness": self._calculate_price_competitiveness(
                        {**supplier, **entry},
                        supplier["service_type"],
                        market_data,
                    ),
                    "quality": entry.get("rating", 0) / 5.0,
                },
                "events": entry.get("events", []),
            }
            history.append(analysis)

        return history

    def _generate_supplier_recommendations(
        self,
        metrics: SupplierMetrics,
        history: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommendations for supplier management."""
        recommendations = []

        # Analizar métricas actuales
        if metrics.reliability_score < 0.7:
            recommendations.append("Revisar acuerdos de nivel de servicio")

        if metrics.price_competitiveness < 0.4:
            recommendations.append("Negociar mejores tarifas")

        if metrics.service_quality < 0.6:
            recommendations.append("Evaluar calidad del servicio")

        if metrics.response_time > 24:
            recommendations.append("Mejorar tiempos de respuesta")

        # Analizar tendencias
        if history:
            recent = history[-3:]  # Últimos 3 períodos

            # Detectar tendencias negativas
            for metric in ["reliability", "competitiveness", "quality"]:
                values = [h["metrics"][metric] for h in recent]
                if all(a > b for a, b in zip(values, values[1:])):
                    recommendations.append(f"Investigar caída en {metric}")

        return recommendations

    def _calculate_supplier_confidence(
        self,
        metrics: SupplierMetrics,
        history: List[Dict[str, Any]],
    ) -> ConfidenceLevel:
        """Calculate confidence in supplier analysis."""
        if not history:
            return ConfidenceLevel.LOW

        # Calcular estabilidad de métricas
        recent = history[-6:]  # Últimos 6 períodos
        stds = []

        for metric in ["reliability", "competitiveness", "quality"]:
            values = [h["metrics"][metric] for h in recent]
            if values:
                stds.append(np.std(values))

        if not stds:
            return ConfidenceLevel.LOW

        # Determinar confianza basada en estabilidad
        avg_std = np.mean(stds)

        if avg_std < 0.1:  # Muy estable
            return ConfidenceLevel.HIGH
        elif avg_std < 0.2:  # Moderadamente estable
            return ConfidenceLevel.MEDIUM
        else:  # Inestable
            return ConfidenceLevel.LOW


class BudgetRecommender:
    """Simple recommender for budget creation and optimization."""

    def __init__(self, max_alternatives: int = 3):
        """Initialize budget recommender.

        Args:
            max_alternatives: Maximum number of alternative packages to suggest
        """
        self.max_alternatives = max_alternatives

    def get_budget_recommendations(
        self,
        current_budget: Budget,
        available_packages: List[TravelPackage],
        target_price: Optional[float] = None,
    ) -> BudgetRecommendation:
        """Generate simple budget recommendations.

        Args:
            current_budget: Current budget being worked on
            available_packages: List of available packages to consider
            target_price: Optional target price for optimization

        Returns:
            Budget recommendation with alternatives
        """
        # Find potential savings
        savings = self._find_potential_savings(current_budget, available_packages)

        # Find alternative packages
        alternatives = self._find_alternatives(
            current_budget, available_packages, target_price
        )

        # Generate explanation
        explanation = self._generate_explanation(savings, alternatives, target_price)

        return BudgetRecommendation(
            budget=current_budget,
            explanation=explanation,
            alternatives=alternatives,
            savings_potential=savings,
        )

    def _find_potential_savings(
        self, budget: Budget, available_packages: List[TravelPackage]
    ) -> float:
        """Find potential savings in current budget."""
        total_savings = 0.0

        # Compare each budget item with available packages
        for item in budget.items:
            cheaper_options = [
                p
                for p in available_packages
                if p.service_type == item.service_type and p.price < item.price
            ]
            if cheaper_options:
                total_savings += item.price - min(p.price for p in cheaper_options)

        return total_savings

    def _find_alternatives(
        self,
        budget: Budget,
        available_packages: List[TravelPackage],
        target_price: Optional[float],
    ) -> List[TravelPackage]:
        """Find alternative packages that could improve the budget."""
        alternatives = []

        for item in budget.items:
            # Find packages of the same type
            similar_packages = [
                p for p in available_packages if p.service_type == item.service_type
            ]

            # Sort by price if target_price exists, otherwise by availability
            if target_price:
                similar_packages.sort(key=lambda p: abs(p.price - target_price))
            else:
                similar_packages.sort(
                    key=lambda p: getattr(p, "availability", 0), reverse=True
                )

            # Add top alternatives
            alternatives.extend(similar_packages[: self.max_alternatives])

        return alternatives[: self.max_alternatives]

    def _generate_explanation(
        self,
        savings: float,
        alternatives: List[TravelPackage],
        target_price: Optional[float],
    ) -> str:
        """Generate simple explanation for the recommendation."""
        explanation = []

        if savings > 0:
            explanation.append(f"Potential savings found: ${savings:.2f}")

        if alternatives:
            explanation.append("\nAlternative packages available:")
            for alt in alternatives:
                explanation.append(f"- {alt.service_type}: ${alt.price:.2f}")

        if target_price and alternatives:
            closest_alt = min(alternatives, key=lambda p: abs(p.price - target_price))
            price_diff = abs(closest_alt.price - target_price)
            explanation.append(
                f"\nClosest to target price (${target_price:.2f}): ${closest_alt.price:.2f}"
            )
            explanation.append(f"Difference: ${price_diff:.2f}")

        return "\n".join(explanation)


@dataclass
class BudgetRecommendation:
    """Simple budget recommendation."""

    budget: Budget
    explanation: str
    alternatives: List[TravelPackage]
    savings_potential: float
