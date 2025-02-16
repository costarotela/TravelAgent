"""Models for report generation system."""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..budget.models import Budget
from ..providers import TravelPackage


class ReportFormat(str, Enum):
    """Available report formats."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class ReportType(str, Enum):
    """Types of reports available."""
    SALES = "sales"
    BUDGET = "budget"
    PROVIDER = "provider"
    DESTINATION = "destination"
    CUSTOM = "custom"


class ReportPeriod(str, Enum):
    """Time periods for reports."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class ReportMetric(BaseModel):
    """Metric for reports."""
    name: str
    value: Union[int, float, str]
    previous_value: Optional[Union[int, float, str]] = None
    change_percentage: Optional[float] = None
    trend: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class ReportChart(BaseModel):
    """Chart configuration for reports."""
    type: str  # pie, bar, line, etc.
    title: str
    data: Dict[str, Union[List[float], List[str]]]
    options: Dict[str, str] = Field(default_factory=dict)


class ReportSection(BaseModel):
    """Section of a report."""
    title: str
    description: Optional[str] = None
    metrics: List[ReportMetric] = Field(default_factory=list)
    charts: List[ReportChart] = Field(default_factory=list)
    tables: List[Dict] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class Report(BaseModel):
    """Complete report model."""
    id: str
    type: ReportType
    title: str
    description: Optional[str] = None
    period: ReportPeriod
    start_date: datetime
    end_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    sections: List[ReportSection] = Field(default_factory=list)
    formats: List[ReportFormat]
    metadata: Dict[str, str] = Field(default_factory=dict)


class ReportTemplate(BaseModel):
    """Template for report generation."""
    id: str
    name: str
    type: ReportType
    description: Optional[str] = None
    section_templates: List[Dict[str, str]]
    formats: List[ReportFormat]
    custom_styles: Optional[Dict[str, str]] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class SalesMetrics(BaseModel):
    """Sales metrics for reports."""
    total_sales: float
    total_budgets: int
    conversion_rate: float
    average_sale: float
    top_destinations: List[Dict[str, Union[str, int, float]]]
    top_packages: List[Dict[str, Union[str, int, float]]]
    revenue_by_provider: Dict[str, float]
    metadata: Dict[str, str] = Field(default_factory=dict)


class ProviderMetrics(BaseModel):
    """Provider performance metrics."""
    provider_name: str
    total_searches: int
    successful_searches: int
    average_response_time: float
    error_rate: float
    total_bookings: int
    revenue: float
    popular_routes: List[Dict[str, Union[str, int]]]
    metadata: Dict[str, str] = Field(default_factory=dict)


class DestinationMetrics(BaseModel):
    """Destination analysis metrics."""
    destination: str
    total_searches: int
    total_bookings: int
    average_price: float
    popular_packages: List[TravelPackage]
    seasonal_demand: Dict[str, int]
    provider_distribution: Dict[str, float]
    metadata: Dict[str, str] = Field(default_factory=dict)


class BudgetMetrics(BaseModel):
    """Budget analysis metrics."""
    total_budgets: int
    approved_budgets: int
    rejected_budgets: int
    expired_budgets: int
    average_processing_time: float
    conversion_rate: float
    average_markup: float
    budgets_by_status: Dict[str, int]
    revenue_projection: float
    metadata: Dict[str, str] = Field(default_factory=dict)
