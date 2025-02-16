"""Travel-related database models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.core.database.base import Base

class TravelPackage(Base):
    """Travel package model."""
    __tablename__ = "travel_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String, index=True)
    origin = Column(String, index=True)
    destination = Column(String, index=True)
    departure_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    price = Column(Float)
    currency = Column(String)
    availability = Column(Integer)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PriceHistory(Base):
    """Price history for travel packages."""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("travel_packages.id"))
    price = Column(Float)
    currency = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    package = relationship("TravelPackage", backref="price_history")

class MarketAnalysis(Base):
    """Market analysis data."""
    __tablename__ = "market_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String, index=True)
    destination = Column(String, index=True)
    avg_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    demand_score = Column(Float)  # 0-1 score indicating demand
    trend = Column(String)  # "up", "down", "stable"
    analysis_date = Column(DateTime, default=datetime.utcnow)
    data = Column(JSON)  # Additional analysis data
