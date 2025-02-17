"""Sistema simple de monitoreo."""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

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
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.logger = logging.getLogger("travel_agency")
        self.db = Database()
        self._init_tables()
    
    def _init_tables(self):
        """Inicializar tablas de métricas y errores."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de métricas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    name TEXT,
                    value REAL,
                    tags JSON
                )
            """)
            
            # Tabla de errores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    error_type TEXT,
                    message TEXT,
                    context JSON
                )
            """)
            
            conn.commit()
    
    def log_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Registrar una métrica."""
        try:
            self.db.save_metric(name, value, tags)
            self.logger.info(f"Metric: {name}={value} tags={tags}")
        except Exception as e:
            self.logger.error(f"Error al registrar métrica: {e}")
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Registrar un error."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO errors (
                        timestamp, error_type, message, context
                    ) VALUES (?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    type(error).__name__,
                    str(error),
                    str(context) if context else None
                ))
                
                conn.commit()
            
            self.logger.error(f"Error: {type(error).__name__} - {str(error)}")
            if context:
                self.logger.error(f"Context: {context}")
        except Exception as e:
            self.logger.error(f"Error al registrar error: {e}")
    
    def get_recent_metrics(self, metric_name: Optional[str] = None, limit: int = 100):
        """Obtener métricas recientes."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if metric_name:
                    cursor.execute("""
                        SELECT * FROM metrics
                        WHERE name = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (metric_name, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM metrics
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (limit,))
                
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error al obtener métricas: {e}")
            return []
    
    def get_recent_errors(self, limit: int = 100):
        """Obtener errores recientes."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM errors
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error al obtener errores: {e}")
            return []

# Instancia global del monitor
monitor = Monitor()
