"""Módulo para el almacenamiento de presupuestos."""
import json
from typing import List, Optional
from datetime import datetime

from .models import Budget, BudgetItem
from decimal import Decimal

class BudgetStorage:
    """Clase para manejar el almacenamiento de presupuestos."""

    def __init__(self, db):
        """Inicializar storage con conexión a base de datos."""
        self.db = db
        self._init_tables()

    def _init_tables(self):
        """Inicializar tablas necesarias."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de presupuestos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP,
                    valid_until TIMESTAMP,
                    customer_name TEXT,
                    items JSON,
                    notes TEXT,
                    status TEXT
                )
            """)
            
            conn.commit()

    def _serialize_date(self, obj):
        """Serializar objetos date y datetime."""
        if isinstance(obj, (datetime)):
            return obj.isoformat()
        return obj

    def _deserialize_date(self, date_str):
        """Deserializar string ISO a date."""
        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None

    def save_budget(self, budget: Budget) -> bool:
        """Guardar un presupuesto en la base de datos."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convertir items a JSON
                items_json = json.dumps([{
                    "type": item.type,
                    "description": item.description,
                    "unit_price": str(item.unit_price),
                    "quantity": item.quantity,
                    "currency": item.currency,
                    "details": {key: self._serialize_date(value) for key, value in item.details.items()}
                } for item in budget.items])
                
                # Insertar presupuesto
                cursor.execute("""
                    INSERT INTO budgets (
                        id, created_at, valid_until, customer_name,
                        items, notes, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    budget.id,
                    budget.created_at.isoformat(),
                    budget.valid_until.isoformat(),
                    budget.customer_name,
                    items_json,
                    budget.notes,
                    budget.status
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error al guardar presupuesto: {e}")
            return False

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Obtener un presupuesto por su ID."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM budgets WHERE id = ?
                """, (budget_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convertir items de JSON
                items_data = json.loads(row["items"])
                items = [
                    BudgetItem(
                        type=item["type"],
                        description=item["description"],
                        unit_price=Decimal(item["unit_price"]),
                        quantity=item["quantity"],
                        currency=item["currency"],
                        details={key: self._deserialize_date(value) if isinstance(value, str) and "T" in value else value for key, value in item["details"].items()}
                    )
                    for item in items_data
                ]
                
                # Crear objeto Budget
                return Budget(
                    id=row["id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    valid_until=datetime.fromisoformat(row["valid_until"]),
                    customer_name=row["customer_name"],
                    items=items,
                    notes=row["notes"],
                    status=row["status"]
                )
                
        except Exception as e:
            print(f"Error al obtener presupuesto: {e}")
            return None

    def get_recent_budgets(self, limit: int = 5) -> List[Budget]:
        """Obtener los presupuestos más recientes."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM budgets
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                
                budgets = []
                for row in cursor.fetchall():
                    # Convertir items de JSON
                    items_data = json.loads(row["items"])
                    items = [
                        BudgetItem(
                            type=item["type"],
                            description=item["description"],
                            unit_price=Decimal(item["unit_price"]),
                            quantity=item["quantity"],
                            currency=item["currency"],
                            details={key: self._deserialize_date(value) if isinstance(value, str) and "T" in value else value for key, value in item["details"].items()}
                        )
                        for item in items_data
                    ]
                    
                    # Crear objeto Budget
                    budget = Budget(
                        id=row["id"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        valid_until=datetime.fromisoformat(row["valid_until"]),
                        customer_name=row["customer_name"],
                        items=items,
                        notes=row["notes"],
                        status=row["status"]
                    )
                    budgets.append(budget)
                
                return budgets
                
        except Exception as e:
            print(f"Error al obtener presupuestos recientes: {e}")
            return []

    def update_budget_status(self, budget_id: str, new_status: str) -> bool:
        """Actualizar el estado de un presupuesto."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE budgets
                    SET status = ?
                    WHERE id = ?
                """, (new_status, budget_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error al actualizar estado del presupuesto: {e}")
            return False
