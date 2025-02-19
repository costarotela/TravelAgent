"""
Base scraper implementation with anti-blocking measures and optimization support.

Este módulo implementa el framework base para scraping con:
1. Medidas anti-bloqueo y gestión de sesiones
2. Soporte para optimización multi-pasada
3. Registro de decisiones de optimización
4. Sistema de métricas integrado
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from prometheus_client import Counter, Histogram

# Métricas para seguimiento de optimización
OPTIMIZATION_PASSES = Counter(
    'optimization_passes_total',
    'Total number of optimization passes performed',
    ['result_type']
)

PRICE_IMPROVEMENTS = Histogram(
    'price_improvements_percentage',
    'Percentage of price improvements found',
    ['pass_number'],
    buckets=[1, 2, 5, 10, 20, 50]
)

@dataclass
class Credentials:
    """Credenciales para login."""
    username: str
    password: str

@dataclass
class OptimizationResult:
    """Resultado de una pasada de optimización."""
    pass_number: int
    original_price: Decimal
    optimized_price: Decimal
    improvement_percentage: float
    changes_applied: List[str]
    timestamp: datetime

class ScraperConfig:
    """Configuration for a scraper instance with optimization settings."""
    
    def __init__(
        self,
        base_url: str,
        login_required: bool = False,
        headless: bool = True,
        proxy_enabled: bool = False,
        user_agent_rotation: bool = True,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        max_retries: int = 3,
        max_optimization_passes: int = 3,
        min_improvement_threshold: float = 1.0,
        credentials: Optional[Credentials] = None
    ):
        self.base_url = base_url
        self.login_required = login_required
        self.headless = headless
        self.proxy_enabled = proxy_enabled
        self.user_agent_rotation = user_agent_rotation
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.max_optimization_passes = max_optimization_passes
        self.min_improvement_threshold = min_improvement_threshold
        self.credentials = credentials

        if login_required and not credentials:
            raise ValueError("Se requieren credenciales cuando login_required es True")

class BaseScraper(ABC):
    """Base class for all scrapers with optimization support."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.optimization_history: List[OptimizationResult] = []
        self.current_pass = 0
        self.best_result: Optional[Dict[str, Any]] = None
        self.driver = None
        self.session_active = False
        self._setup_logging()

    def _setup_logging(self):
        """Setup scraper-specific logging."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def optimize(self, initial_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[OptimizationResult]]:
        """
        Realiza múltiples pasadas de optimización sobre los datos iniciales.
        
        Args:
            initial_data: Datos iniciales a optimizar
            
        Returns:
            Tuple con los datos optimizados y el historial de optimización
        """
        self.best_result = initial_data
        current_price = Decimal(str(initial_data['precio']))
        
        while self.current_pass < self.config.max_optimization_passes:
            self.current_pass += 1
            self.logger.info(f"Iniciando pasada de optimización {self.current_pass}")
            
            try:
                # Realizar pasada de optimización
                optimized_data = await self._optimization_pass(self.best_result)
                optimized_price = Decimal(str(optimized_data['precio']))
                
                # Calcular mejora
                improvement = ((current_price - optimized_price) / current_price) * 100
                
                # Registrar resultado
                result = OptimizationResult(
                    pass_number=self.current_pass,
                    original_price=current_price,
                    optimized_price=optimized_price,
                    improvement_percentage=float(improvement),
                    changes_applied=self._get_changes(self.best_result, optimized_data),
                    timestamp=datetime.now()
                )
                
                self.optimization_history.append(result)
                PRICE_IMPROVEMENTS.labels(pass_number=self.current_pass).observe(float(improvement))
                
                # Verificar si la mejora es significativa
                if improvement > self.config.min_improvement_threshold:
                    self.best_result = optimized_data
                    current_price = optimized_price
                    OPTIMIZATION_PASSES.labels(result_type='improvement').inc()
                    self.logger.info(f"Mejora encontrada: {improvement:.2f}%")
                else:
                    OPTIMIZATION_PASSES.labels(result_type='no_improvement').inc()
                    self.logger.info(f"No se encontró mejora significativa: {improvement:.2f}%")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error en pasada de optimización {self.current_pass}: {str(e)}")
                OPTIMIZATION_PASSES.labels(result_type='error').inc()
                break
        
        return self.best_result, self.optimization_history

    @abstractmethod
    async def _optimization_pass(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implementación específica de una pasada de optimización.
        Debe ser implementada por las clases derivadas.
        """
        pass

    def _get_changes(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> List[str]:
        """Identifica los cambios entre dos versiones de datos."""
        changes = []
        
        if old_data['precio'] != new_data['precio']:
            changes.append(f"Cambio de precio: {old_data['precio']} -> {new_data['precio']}")
            
        # Agregar más comparaciones según sea necesario
        
        return changes
