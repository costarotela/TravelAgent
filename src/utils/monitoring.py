"""Sistema simple de monitoreo."""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from prometheus_client import Counter as PrometheusCounter, Histogram

from .database import Database


class Monitor:
    """Clase para monitoreo simple."""

    def __init__(self):
        """Inicializar monitor."""
        # Configurar logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            filename=log_dir / "travel_agency.log",
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        self.logger = logging.getLogger("travel_agency")
        self.db = Database()
        self._init_tables()

    def _init_tables(self):
        """Inicializar tablas de métricas y errores."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Tabla de métricas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    metric_name TEXT,
                    metric_value REAL,
                    tags JSON
                )
            """
            )

            # Tabla de errores
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    error_type TEXT,
                    error_message TEXT,
                    tags JSON
                )
            """
            )

            conn.commit()

    def log_metric(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ):
        """Registrar una métrica."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO metrics (
                        timestamp, metric_name, metric_value, tags
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        datetime.now().isoformat(),
                        name,
                        value,
                        json.dumps(tags) if tags else None,
                    ),
                )

                conn.commit()

            self.logger.info(f"Metric: {name}={value} tags={tags}")
        except Exception as e:
            self.logger.error(f"Error al registrar métrica: {e}")

    def log_error(self, error: Exception, tags: Optional[Dict[str, Any]] = None):
        """Registrar un error."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO errors (
                        timestamp, error_type, error_message, tags
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        datetime.now().isoformat(),
                        type(error).__name__,
                        str(error),
                        json.dumps(tags) if tags else None,
                    ),
                )

                conn.commit()

            self.logger.error(f"Error: {type(error).__name__} - {str(error)}")
            if tags:
                self.logger.error(f"Context: {tags}")
        except Exception as e:
            self.logger.error(f"Error al registrar error: {e}")


def setup_monitoring():
    """Configura las métricas de monitoreo."""
    # Métricas para el detector de cambios
    if "changes_detected" not in METRICS:
        METRICS["changes_detected"] = PrometheusCounter(
            "changes_detected_total", "Total de cambios detectados", ["tipo"]
        )

    if "update_duration" not in METRICS:
        METRICS["update_duration"] = Histogram(
            "update_duration_seconds", "Duración de las actualizaciones", ["provider"]
        )

    if "cache_hits" not in METRICS:
        METRICS["cache_hits"] = PrometheusCounter(
            "cache_hits_total", "Total de aciertos en caché", ["cache_type"]
        )

    if "cache_misses" not in METRICS:
        METRICS["cache_misses"] = PrometheusCounter(
            "cache_misses_total", "Total de fallos en caché", ["cache_type"]
        )


def get_metrics_db_path() -> str:
    """Obtener ruta a la base de datos de métricas."""
    return str(Path("data/metrics.db").absolute())


# Instancia global del monitor
METRICS = {}
setup_monitoring()
monitor = Monitor()
