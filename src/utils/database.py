"""Base de datos SQLite para la agencia de viajes."""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager


class Database:
    """Clase para manejar la base de datos SQLite."""

    def __init__(self):
        """Inicializar la base de datos."""
        self.db_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "travel_agency.db"
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        """Obtener conexión a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Inicializar las tablas de la base de datos."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tabla de presupuestos
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                    id TEXT PRIMARY KEY,
                    customer_name TEXT,
                    created_at TEXT NOT NULL,
                    valid_until TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft'
                )
            """
            )

            # Tabla de items de presupuesto
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS budget_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    budget_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    unit_price TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    details TEXT NOT NULL,
                    FOREIGN KEY (budget_id) REFERENCES budgets(id)
                )
            """
            )

            # Tabla de búsquedas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT,
                    adults INTEGER DEFAULT 1,
                    children INTEGER DEFAULT 0,
                    infants INTEGER DEFAULT 0,
                    class_type TEXT,
                    search_time TEXT NOT NULL
                )
            """
            )

            # Tabla de resultados de búsqueda
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS search_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_id INTEGER NOT NULL,
                    flight_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    return_date TEXT,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    availability INTEGER,
                    details TEXT,
                    raw_data TEXT,
                    FOREIGN KEY (search_id) REFERENCES searches(id)
                )
            """
            )

            # Tabla de métricas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    tags TEXT,
                    timestamp TEXT NOT NULL
                )
            """
            )

            conn.commit()

    def save_budget(self, budget_dict: Dict[str, Any]) -> bool:
        """Guardar un presupuesto."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Insertar presupuesto
                cursor.execute(
                    """
                    INSERT INTO budgets (id, customer_name, created_at, valid_until, status)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        budget_dict["id"],
                        budget_dict["customer_name"],
                        budget_dict["created_at"],
                        budget_dict["valid_until"],
                        budget_dict["status"],
                    ),
                )

                # Insertar items
                for item in budget_dict["items"]:
                    cursor.execute(
                        """
                        INSERT INTO budget_items (
                            budget_id, description, unit_price,
                            quantity, currency, details
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            budget_dict["id"],
                            item["description"],
                            item["unit_price"],
                            item["quantity"],
                            item["currency"],
                            json.dumps(item["details"]),
                        ),
                    )

                conn.commit()
                return True
        except Exception as e:
            print(f"Error al guardar presupuesto: {e}")
            return False

    def get_budget(self, budget_id: str) -> Optional[Dict[str, Any]]:
        """Obtener un presupuesto por su ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener presupuesto
                cursor.execute(
                    """
                    SELECT * FROM budgets WHERE id = ?
                """,
                    (budget_id,),
                )
                budget_row = cursor.fetchone()
                if not budget_row:
                    return None

                budget = dict(budget_row)

                # Obtener items
                cursor.execute(
                    """
                    SELECT * FROM budget_items WHERE budget_id = ?
                """,
                    (budget_id,),
                )
                items = []
                for row in cursor.fetchall():
                    item = dict(row)
                    item["details"] = json.loads(item["details"])
                    items.append(item)

                budget["items"] = items
                return budget
        except Exception as e:
            print(f"Error al obtener presupuesto: {e}")
            return None

    def get_recent_budgets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener los presupuestos más recientes."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener presupuestos recientes
                cursor.execute(
                    """
                    SELECT * FROM budgets
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )
                budgets = []

                for row in cursor.fetchall():
                    budget = dict(row)

                    # Obtener items para cada presupuesto
                    cursor.execute(
                        """
                        SELECT * FROM budget_items
                        WHERE budget_id = ?
                    """,
                        (budget["id"],),
                    )

                    items = []
                    for item_row in cursor.fetchall():
                        item = dict(item_row)
                        item["details"] = json.loads(item["details"])
                        items.append(item)

                    budget["items"] = items
                    budgets.append(budget)

                return budgets
        except Exception as e:
            print(f"Error al obtener presupuestos recientes: {e}")
            return []

    def update_budget(self, budget_dict: Dict[str, Any]) -> bool:
        """Actualizar un presupuesto existente."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Actualizar presupuesto
                cursor.execute(
                    """
                    UPDATE budgets
                    SET customer_name = ?,
                        valid_until = ?,
                        status = ?
                    WHERE id = ?
                """,
                    (
                        budget_dict["customer_name"],
                        budget_dict["valid_until"],
                        budget_dict["status"],
                        budget_dict["id"],
                    ),
                )

                # Eliminar items antiguos
                cursor.execute(
                    """
                    DELETE FROM budget_items
                    WHERE budget_id = ?
                """,
                    (budget_dict["id"],),
                )

                # Insertar nuevos items
                for item in budget_dict["items"]:
                    cursor.execute(
                        """
                        INSERT INTO budget_items (
                            budget_id, description, unit_price,
                            quantity, currency, details
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            budget_dict["id"],
                            item["description"],
                            item["unit_price"],
                            item["quantity"],
                            item["currency"],
                            json.dumps(item["details"]),
                        ),
                    )

                conn.commit()
                return True
        except Exception as e:
            print(f"Error al actualizar presupuesto: {e}")
            return False

    def update_budget_status(self, budget_id: str, new_status: str) -> bool:
        """Actualizar el estado de un presupuesto."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE budgets
                    SET status = ?
                    WHERE id = ?
                """,
                    (new_status, budget_id),
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error al actualizar estado: {e}")
            return False

    def save_metric(self, metric: Dict[str, Any]) -> bool:
        """Guardar una métrica."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO metrics (name, value, tags, timestamp)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        metric["name"],
                        metric["value"],
                        json.dumps(metric.get("tags", {})),
                        metric.get("timestamp") or datetime.now().isoformat(),
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error al guardar métrica: {e}")
            return False

    def save_search(self, provider: str, criteria: Dict[str, Any]) -> int:
        """Guardar una búsqueda y retornar su ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Insertar búsqueda
                cursor.execute(
                    """
                    INSERT INTO searches (
                        provider, origin, destination, departure_date,
                        return_date, adults, children, infants, class_type, search_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        provider,
                        criteria.get("origin"),
                        criteria.get("destination"),
                        criteria.get("departure_date"),
                        criteria.get("return_date"),
                        criteria.get("adults", 1),
                        criteria.get("children", 0),
                        criteria.get("infants", 0),
                        criteria.get("class_type"),
                        datetime.now().isoformat(),
                    ),
                )

                search_id = cursor.lastrowid
                conn.commit()
                return search_id
        except Exception as e:
            print(f"Error al guardar búsqueda: {e}")
            return -1

    def save_search_results(self, search_id: int, results: List[Dict[str, Any]]):
        """Guardar resultados de búsqueda."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Insertar resultados
                for result in results:
                    cursor.execute(
                        """
                        INSERT INTO search_results (
                            search_id, flight_id, provider, origin, destination,
                            departure_date, return_date, price, currency, availability, details, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            search_id,
                            result["id"],
                            result["provider"],
                            result["origin"],
                            result["destination"],
                            result["departure_date"],
                            result.get("return_date"),
                            result["price"],
                            result["currency"],
                            result.get("availability", 0),
                            json.dumps(result.get("details", {})),
                            json.dumps(result.get("raw_data", {})),
                        ),
                    )

                conn.commit()
        except Exception as e:
            print(f"Error al guardar resultados de búsqueda: {e}")

    def get_recent_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener búsquedas recientes."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener búsquedas recientes
                cursor.execute(
                    """
                    SELECT * FROM searches
                    ORDER BY search_time DESC
                    LIMIT ?
                """,
                    (limit,),
                )
                searches = []

                for row in cursor.fetchall():
                    search = dict(row)
                    searches.append(search)

                return searches
        except Exception as e:
            print(f"Error al obtener búsquedas recientes: {e}")
            return []

    def get_search_results(self, search_id: int) -> List[Dict[str, Any]]:
        """Obtener resultados de una búsqueda específica."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener resultados
                cursor.execute(
                    """
                    SELECT * FROM search_results
                    WHERE search_id = ?
                """,
                    (search_id,),
                )
                results = []

                for row in cursor.fetchall():
                    result = dict(row)
                    result["details"] = json.loads(result["details"])
                    result["raw_data"] = json.loads(result["raw_data"])
                    results.append(result)

                # Ordenar por precio (menor precio primero)
                results.sort(key=lambda x: x["price"])
                return results
        except Exception as e:
            print(f"Error al obtener resultados de búsqueda: {e}")
            return []

    def get_metrics(
        self, metric_name: str, from_time: datetime = None, to_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """Obtener métricas filtradas por nombre y rango de tiempo."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Obtener métricas
                cursor.execute(
                    """
                    SELECT * FROM metrics
                    WHERE name = ?
                """,
                    (metric_name,),
                )
                metrics = []

                for row in cursor.fetchall():
                    metric = dict(row)
                    metric["tags"] = json.loads(metric["tags"])
                    metrics.append(metric)

                if from_time:
                    metrics = [
                        metric
                        for metric in metrics
                        if datetime.fromisoformat(metric["timestamp"]) >= from_time
                    ]
                if to_time:
                    metrics = [
                        metric
                        for metric in metrics
                        if datetime.fromisoformat(metric["timestamp"]) <= to_time
                    ]

                # Ordenar por fecha de creación (más recientes primero)
                metrics.sort(key=lambda x: x["timestamp"], reverse=True)
                return metrics
        except Exception as e:
            print(f"Error al obtener métricas: {e}")
            return []
