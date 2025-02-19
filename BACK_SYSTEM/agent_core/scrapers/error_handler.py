"""Manejador de errores para los scrapers."""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

from prometheus_client import Counter, Histogram

# Métricas de Prometheus
SCRAPER_ERRORS = Counter(
    'scraper_errors_total',
    'Número total de errores por tipo',
    ['scraper', 'error_type']
)

SCRAPER_RETRIES = Counter(
    'scraper_retries_total',
    'Número total de reintentos por operación',
    ['scraper', 'operation']
)

SCRAPER_OPERATION_TIME = Histogram(
    'scraper_operation_duration_seconds',
    'Tiempo de ejecución de operaciones del scraper',
    ['scraper', 'operation']
)

class ScraperError(Exception):
    """Error base para errores del scraper."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error

class ConnectionError(ScraperError):
    """Error de conexión."""
    pass

class AuthenticationError(ScraperError):
    """Error de autenticación."""
    pass

class DataExtractionError(ScraperError):
    """Error al extraer datos."""
    pass

class BlockedError(ScraperError):
    """Error por bloqueo del sitio."""
    pass

class ErrorHandler:
    """Manejador de errores para los scrapers."""
    
    def __init__(self, scraper_name: str, logger: Optional[logging.Logger] = None):
        self.scraper_name = scraper_name
        self.logger = logger or logging.getLogger(__name__)
        
        # Configuración de reintentos por tipo de error
        self.retry_config: Dict[Type[ScraperError], Dict[str, int]] = {
            ConnectionError: {'max_retries': 3, 'base_delay': 2},
            AuthenticationError: {'max_retries': 2, 'base_delay': 1},
            DataExtractionError: {'max_retries': 2, 'base_delay': 1},
            BlockedError: {'max_retries': 1, 'base_delay': 5}
        }

    def with_retry(self, operation: str):
        """Decorador para ejecutar operaciones con reintentos."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_error = None
                start_time = time.time()
                
                for attempt in range(self.retry_config[ConnectionError]['max_retries']):
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Registrar métricas de éxito
                        duration = time.time() - start_time
                        SCRAPER_OPERATION_TIME.labels(
                            scraper=self.scraper_name,
                            operation=operation
                        ).observe(duration)
                        
                        return result
                        
                    except Exception as e:
                        error = self.handle_error(e, operation)
                        last_error = error
                        
                        # Registrar error
                        SCRAPER_ERRORS.labels(
                            scraper=self.scraper_name,
                            error_type=type(error).__name__
                        ).inc()
                        
                        # Verificar si debemos reintentar
                        config = self.retry_config.get(
                            type(error), 
                            {'max_retries': 0, 'base_delay': 1}
                        )
                        
                        if attempt < config['max_retries'] - 1:
                            delay = config['base_delay'] * (2 ** attempt)
                            
                            self.logger.warning(
                                f"Error en {operation} (intento {attempt + 1}): {str(error)}. "
                                f"Reintentando en {delay} segundos..."
                            )
                            
                            SCRAPER_RETRIES.labels(
                                scraper=self.scraper_name,
                                operation=operation
                            ).inc()
                            
                            await asyncio.sleep(delay)
                            continue
                        
                        # Si llegamos aquí, se agotaron los reintentos
                        self.logger.error(
                            f"Error final en {operation} después de {attempt + 1} intentos: {str(error)}",
                            exc_info=error.original_error
                        )
                        raise error
                
                raise last_error  # No debería llegar aquí, pero por si acaso
            
            return wrapper
        return decorator

    def handle_error(self, error: Exception, operation: str) -> ScraperError:
        """Convierte errores genéricos en ScraperError específicos."""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Mapeo de errores comunes
        if isinstance(error, ScraperError):
            return error
            
        if any(term in error_type or term in error_msg 
               for term in ['connection', 'timeout', 'socket']):
            return ConnectionError(f"Error de conexión: {str(error)}", error)
            
        if any(term in error_type or term in error_msg 
                for term in ['authentication', 'login', 'credentials']):
            return AuthenticationError(f"Error de autenticación: {str(error)}", error)
            
        if any(term in error_type or term in error_msg 
                for term in ['nosuchelement', 'invalidselector', 'elementnotfound', 'element not found']):
            return DataExtractionError(f"Error extrayendo datos: {str(error)}", error)
            
        if any(term in error_type or term in error_msg 
                for term in ['blocked', 'captcha', 'ratelimit']):
            return BlockedError(f"Acceso bloqueado por el sitio: {str(error)}", error)
        
        # Si no coincide con ningún tipo específico, devolver error genérico
        return ScraperError(f"Error en operación {operation}: {str(error)}", error)

    def log_operation(self, operation: str, **kwargs):
        """Registra una operación en el log."""
        msg = f"Operación: {operation}"
        if kwargs:
            msg += f" - Parámetros: {kwargs}"
        self.logger.info(msg)
