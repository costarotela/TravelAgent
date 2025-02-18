"""Sistema de monitoreo para el proveedor OLA."""

import logging
from typing import Dict
from prometheus_client import Gauge, Counter, start_http_server

logger = logging.getLogger(__name__)

class OLAMonitor:
    """Monitor para métricas del proveedor OLA."""
    
    def __init__(self, port: int = 9090):
        """Inicializar monitor OLA.
        
        Args:
            port: Puerto para exponer métricas de Prometheus
        """
        # Métricas de paquetes
        self.paquetes_nuevos = Gauge(
            'ola_new_packages',
            'Cantidad de paquetes nuevos detectados',
            ['destino']
        )
        self.paquetes_actualizados = Gauge(
            'ola_updated_packages',
            'Cantidad de paquetes actualizados detectados',
            ['destino']
        )
        self.paquetes_eliminados = Gauge(
            'ola_deleted_packages',
            'Cantidad de paquetes eliminados detectados',
            ['destino']
        )
        
        # Métricas de precios
        self.precio_promedio = Gauge(
            'ola_average_price',
            'Precio promedio de paquetes',
            ['destino', 'moneda']
        )
        self.precio_minimo = Gauge(
            'ola_min_price',
            'Precio mínimo de paquetes',
            ['destino', 'moneda']
        )
        self.precio_maximo = Gauge(
            'ola_max_price',
            'Precio máximo de paquetes',
            ['destino', 'moneda']
        )
        
        # Métricas de rendimiento
        self.tiempo_actualizacion = Gauge(
            'ola_update_time_seconds',
            'Tiempo de actualización en segundos',
            ['destino']
        )
        self.error_counter = Counter(
            'ola_update_errors_total',
            'Cantidad total de errores en actualizaciones',
            ['tipo_error']
        )
        self.scraping_duration = Gauge(
            'ola_scraping_duration_seconds',
            'Duración del proceso de scraping en segundos',
            ['destino']
        )
        
        # Métricas de disponibilidad
        self.disponibilidad = Gauge(
            'ola_availability_percentage',
            'Porcentaje de paquetes disponibles',
            ['destino']
        )
        
        # Iniciar servidor de métricas
        try:
            start_http_server(port)
            logger.info(f"Servidor de métricas iniciado en puerto {port}")
        except Exception as e:
            logger.error(f"Error iniciando servidor de métricas: {e}")
            raise

    def update_package_metrics(self, stats: Dict, destino: str):
        """Actualizar métricas de paquetes.
        
        Args:
            stats: Diccionario con estadísticas de actualización
            destino: Destino de los paquetes
        """
        self.paquetes_nuevos.labels(destino=destino).set(
            stats.get('total_nuevos', 0)
        )
        self.paquetes_actualizados.labels(destino=destino).set(
            stats.get('total_actualizados', 0)
        )
        self.paquetes_eliminados.labels(destino=destino).set(
            stats.get('total_eliminados', 0)
        )

    def update_price_metrics(self, stats: Dict, destino: str, moneda: str):
        """Actualizar métricas de precios.
        
        Args:
            stats: Diccionario con estadísticas de precios
            destino: Destino de los paquetes
            moneda: Moneda de los precios
        """
        self.precio_promedio.labels(destino=destino, moneda=moneda).set(
            stats.get('precio_promedio', 0)
        )
        self.precio_minimo.labels(destino=destino, moneda=moneda).set(
            stats.get('precio_minimo', 0)
        )
        self.precio_maximo.labels(destino=destino, moneda=moneda).set(
            stats.get('precio_maximo', 0)
        )

    def log_error(self, tipo_error: str = 'general'):
        """Registrar un error en el contador.
        
        Args:
            tipo_error: Tipo de error ocurrido
        """
        self.error_counter.labels(tipo_error=tipo_error).inc()
        logger.error(f"Error registrado: {tipo_error}")

    def update_performance_metrics(self, tiempo: float, destino: str):
        """Actualizar métricas de rendimiento.
        
        Args:
            tiempo: Tiempo de actualización en segundos
            destino: Destino actualizado
        """
        self.tiempo_actualizacion.labels(destino=destino).set(tiempo)

    def update_scraping_duration(self, duracion: float, destino: str):
        """Actualizar duración del scraping.
        
        Args:
            duracion: Duración del scraping en segundos
            destino: Destino procesado
        """
        self.scraping_duration.labels(destino=destino).set(duracion)

    def update_availability(self, porcentaje: float, destino: str):
        """Actualizar métrica de disponibilidad.
        
        Args:
            porcentaje: Porcentaje de disponibilidad
            destino: Destino analizado
        """
        self.disponibilidad.labels(destino=destino).set(porcentaje)
