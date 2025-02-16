"""Módulo que integra estimación de impacto y calibración de confianza."""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.core.analysis.impact_estimator import ImpactEstimator, MarketCondition
from src.core.analysis.confidence_calibrator import ConfidenceCalibrator, CalibrationMetrics

@dataclass
class AdvancedEstimation:
    """Resultado de estimación avanzada."""
    estimated_impact: float
    raw_confidence: float
    calibrated_confidence: float
    market_condition: MarketCondition
    calibration_metrics: CalibrationMetrics
    recommendation: str
    risk_level: str

class AdvancedEstimator:
    """Sistema integrado de estimación y calibración."""
    
    def __init__(self):
        self.impact_estimator = ImpactEstimator()
        self.confidence_calibrator = ConfidenceCalibrator()
        
    async def analyze(
        self,
        action_type: str,
        origin: str,
        destination: str,
        market_data: Dict,
        historical_data: Optional[List] = None
    ) -> AdvancedEstimation:
        """Realiza análisis completo de una acción potencial."""
        # Estimar impacto
        impact_estimation = await self.impact_estimator.estimate_impact(
            action_type,
            origin,
            destination,
            market_data,
            historical_data
        )
        
        # Calibrar confianza
        calibrated_confidence, metrics = await self.confidence_calibrator.calibrate_confidence(
            impact_estimation['confidence'],
            action_type,
            market_data,
            historical_data
        )
        
        # Generar recomendación
        recommendation = self._generate_recommendation(
            impact_estimation['estimated_impact'],
            calibrated_confidence,
            impact_estimation['market_condition']
        )
        
        # Evaluar nivel de riesgo
        risk_level = self._evaluate_risk(
            impact_estimation['estimated_impact'],
            calibrated_confidence,
            impact_estimation['market_condition']
        )
        
        return AdvancedEstimation(
            estimated_impact=impact_estimation['estimated_impact'],
            raw_confidence=impact_estimation['confidence'],
            calibrated_confidence=calibrated_confidence,
            market_condition=impact_estimation['market_condition'],
            calibration_metrics=metrics,
            recommendation=recommendation,
            risk_level=risk_level
        )
    
    def _generate_recommendation(
        self,
        impact: float,
        confidence: float,
        market: MarketCondition
    ) -> str:
        """Genera una recomendación basada en el análisis."""
        if confidence < 0.3:
            return "Investigar más - confianza muy baja"
            
        if impact < 0.4:
            return "No recomendado - impacto bajo"
            
        if market.volatility > 0.3:
            return "Precaución - mercado volátil"
            
        if impact > 0.7 and confidence > 0.6:
            return "Altamente recomendado"
            
        if impact > 0.5 and confidence > 0.5:
            return "Recomendado con monitoreo"
            
        return "Considerar con precaución"
    
    def _evaluate_risk(
        self,
        impact: float,
        confidence: float,
        market: MarketCondition
    ) -> str:
        """Evalúa el nivel de riesgo de la acción."""
        risk_score = (
            (1 - confidence) * 0.4 +
            market.volatility * 0.3 +
            (1 - impact) * 0.3
        )
        
        if risk_score < 0.2:
            return "muy_bajo"
        elif risk_score < 0.4:
            return "bajo"
        elif risk_score < 0.6:
            return "medio"
        elif risk_score < 0.8:
            return "alto"
        return "muy_alto"
    
    def update_models(
        self,
        action_type: str,
        predicted_confidence: float,
        actual_outcome: float,
        market_data: Dict
    ) -> None:
        """Actualiza ambos modelos con nuevos datos."""
        # Actualizar calibrador de confianza
        self.confidence_calibrator.update_calibration(
            predicted_confidence,
            actual_outcome,
            action_type
        )
        
        # Aquí podríamos agregar actualizaciones al estimador de impacto
        # cuando implementemos aprendizaje en tiempo real
