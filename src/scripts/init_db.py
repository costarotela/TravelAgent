"""Database initialization script."""
import sys
import os

# Agregar el directorio src al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.database.base import db
from src.core.models.travel import TravelPackage, PriceHistory, MarketAnalysis

def init_database():
    """Initialize the database and create all tables."""
    try:
        print("Creating database tables...")
        db.create_tables()
        print("Database tables created successfully!")
        return True
    except Exception as e:
        print(f"Error creating database tables: {e}")
        return False

if __name__ == "__main__":
    init_database()
