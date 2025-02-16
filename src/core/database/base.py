"""Database configuration and base models."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from src.core.config.settings import settings

# Base class for all database models
Base = declarative_base()

class Database:
    """Database connection and session management."""
    
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_session(self):
        """Get a database session with context management."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Global database instance
db = Database()
