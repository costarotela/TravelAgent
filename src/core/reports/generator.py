"""Report generator for travel agency system."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from uuid import uuid4

from ..budget.models import Budget, BudgetStatus
from ..providers import TravelPackage
from .models import (
    BudgetMetrics,
    DestinationMetrics,
    ProviderMetrics,
    Report,
    ReportFormat,
    ReportPeriod,
    ReportSection,
    ReportTemplate,
    ReportType,
    SalesMetrics,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generator for creating various types of reports."""

    def __init__(self):
        """Initialize report generator."""
        self._templates: Dict[str, ReportTemplate] = {}

    def generate_report(
        self,
        type: ReportType,
        period: ReportPeriod,
        start_date: datetime,
        end_date: datetime,
        template_id: Optional[str] = None,
        formats: Optional[List[ReportFormat]] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Report:
        """Generate a new report.
        
        Args:
            type: Type of report to generate
            period: Time period for the report
            start_date: Start date for data
            end_date: End date for data
            template_id: Optional template to use
            formats: Output formats
            metadata: Optional metadata
        
        Returns:
            Generated Report object
        """
        # Get template if specified
        template = self._templates.get(template_id) if template_id else None
        
        # Use template formats or defaults
        report_formats = formats or (
            template.formats if template else [ReportFormat.PDF]
        )

        # Create report sections based on type
        sections = self._generate_sections(
            type,
            start_date,
            end_date,
            template
        )

        # Create report
        report = Report(
            id=str(uuid4()),
            type=type,
            title=self._get_report_title(type, period),
            period=period,
            start_date=start_date,
            end_date=end_date,
            created_by="system",
            sections=sections,
            formats=report_formats,
            metadata=metadata or {}
        )

        logger.info(
            f"Generated {type} report {report.id} for period {period}"
        )
        return report

    def register_template(self, template: ReportTemplate) -> None:
        """Register a new report template.
        
        Args:
            template: Template to register
        """
        self._templates[template.id] = template
        logger.info(f"Registered template {template.id}")

    def _generate_sections(
        self,
        type: ReportType,
        start_date: datetime,
        end_date: datetime,
        template: Optional[ReportTemplate] = None
    ) -> List[ReportSection]:
        """Generate sections based on report type."""
        if type == ReportType.SALES:
            return self._generate_sales_sections(start_date, end_date)
        elif type == ReportType.BUDGET:
            return self._generate_budget_sections(start_date, end_date)
        elif type == ReportType.PROVIDER:
            return self._generate_provider_sections(start_date, end_date)
        elif type == ReportType.DESTINATION:
            return self._generate_destination_sections(start_date, end_date)
        elif type == ReportType.CUSTOM and template:
            return self._generate_custom_sections(
                template,
                start_date,
                end_date
            )
        else:
            raise ValueError(f"Unsupported report type: {type}")

    def _generate_sales_sections(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[ReportSection]:
        """Generate sales report sections."""
        # Here we would get actual metrics from database
        # For now, using dummy data
        metrics = SalesMetrics(
            total_sales=100000.0,
            total_budgets=50,
            conversion_rate=0.6,
            average_sale=2000.0,
            top_destinations=[
                {"name": "Paris", "sales": 15, "revenue": 30000.0},
                {"name": "London", "sales": 12, "revenue": 24000.0}
            ],
            top_packages=[
                {"id": "PKG1", "sales": 8, "revenue": 16000.0},
                {"id": "PKG2", "sales": 6, "revenue": 12000.0}
            ],
            revenue_by_provider={
                "OLA": 40000.0,
                "AERO": 35000.0,
                "DESPEGAR": 25000.0
            }
        )

        sections = [
            ReportSection(
                title="Sales Overview",
                metrics=[
                    {"name": "Total Sales", "value": metrics.total_sales},
                    {"name": "Total Budgets", "value": metrics.total_budgets},
                    {
                        "name": "Conversion Rate",
                        "value": f"{metrics.conversion_rate:.1%}"
                    },
                    {
                        "name": "Average Sale",
                        "value": metrics.average_sale
                    }
                ]
            ),
            ReportSection(
                title="Top Destinations",
                charts=[{
                    "type": "pie",
                    "title": "Revenue by Destination",
                    "data": {
                        "labels": [d["name"] for d in metrics.top_destinations],
                        "values": [d["revenue"] for d in metrics.top_destinations]
                    }
                }]
            ),
            ReportSection(
                title="Provider Performance",
                charts=[{
                    "type": "bar",
                    "title": "Revenue by Provider",
                    "data": metrics.revenue_by_provider
                }]
            )
        ]

        return sections

    def _generate_budget_sections(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[ReportSection]:
        """Generate budget report sections."""
        # Here we would get actual metrics from database
        metrics = BudgetMetrics(
            total_budgets=100,
            approved_budgets=60,
            rejected_budgets=20,
            expired_budgets=20,
            average_processing_time=48.5,
            conversion_rate=0.6,
            average_markup=0.15,
            budgets_by_status={
                "draft": 10,
                "pending": 30,
                "approved": 60,
                "rejected": 20,
                "expired": 20
            },
            revenue_projection=150000.0
        )

        sections = [
            ReportSection(
                title="Budget Overview",
                metrics=[
                    {"name": "Total Budgets", "value": metrics.total_budgets},
                    {
                        "name": "Approved Budgets",
                        "value": metrics.approved_budgets
                    },
                    {
                        "name": "Conversion Rate",
                        "value": f"{metrics.conversion_rate:.1%}"
                    }
                ]
            ),
            ReportSection(
                title="Budget Status Distribution",
                charts=[{
                    "type": "pie",
                    "title": "Budgets by Status",
                    "data": metrics.budgets_by_status
                }]
            ),
            ReportSection(
                title="Processing Metrics",
                metrics=[
                    {
                        "name": "Avg. Processing Time",
                        "value": f"{metrics.average_processing_time:.1f}h"
                    },
                    {
                        "name": "Avg. Markup",
                        "value": f"{metrics.average_markup:.1%}"
                    },
                    {
                        "name": "Revenue Projection",
                        "value": metrics.revenue_projection
                    }
                ]
            )
        ]

        return sections

    def _generate_provider_sections(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[ReportSection]:
        """Generate provider report sections."""
        # Here we would get actual metrics from database
        metrics = {
            "OLA": ProviderMetrics(
                provider_name="OLA",
                total_searches=1000,
                successful_searches=950,
                average_response_time=0.8,
                error_rate=0.05,
                total_bookings=100,
                revenue=200000.0,
                popular_routes=[
                    {"route": "NYC-LAX", "bookings": 30},
                    {"route": "LAX-SFO", "bookings": 25}
                ]
            ),
            "AERO": ProviderMetrics(
                provider_name="AERO",
                total_searches=800,
                successful_searches=760,
                average_response_time=1.2,
                error_rate=0.05,
                total_bookings=80,
                revenue=160000.0,
                popular_routes=[
                    {"route": "MIA-NYC", "bookings": 20},
                    {"route": "BOS-CHI", "bookings": 15}
                ]
            )
        }

        sections = [
            ReportSection(
                title="Provider Overview",
                charts=[{
                    "type": "bar",
                    "title": "Provider Performance",
                    "data": {
                        "Revenue": [m.revenue for m in metrics.values()],
                        "Bookings": [m.total_bookings for m in metrics.values()]
                    }
                }]
            )
        ]

        # Add section for each provider
        for provider_metrics in metrics.values():
            sections.append(
                ReportSection(
                    title=f"{provider_metrics.provider_name} Metrics",
                    metrics=[
                        {
                            "name": "Success Rate",
                            "value": f"{provider_metrics.successful_searches / provider_metrics.total_searches:.1%}"
                        },
                        {
                            "name": "Avg Response Time",
                            "value": f"{provider_metrics.average_response_time:.1f}s"
                        },
                        {
                            "name": "Error Rate",
                            "value": f"{provider_metrics.error_rate:.1%}"
                        }
                    ],
                    charts=[{
                        "type": "pie",
                        "title": "Popular Routes",
                        "data": {
                            r["route"]: r["bookings"]
                            for r in provider_metrics.popular_routes
                        }
                    }]
                )
            )

        return sections

    def _generate_destination_sections(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[ReportSection]:
        """Generate destination report sections."""
        # Here we would get actual metrics from database
        metrics = {
            "Paris": DestinationMetrics(
                destination="Paris",
                total_searches=500,
                total_bookings=50,
                average_price=1500.0,
                popular_packages=[],  # Would contain actual packages
                seasonal_demand={
                    "Spring": 150,
                    "Summer": 200,
                    "Fall": 100,
                    "Winter": 50
                },
                provider_distribution={
                    "OLA": 0.4,
                    "AERO": 0.35,
                    "DESPEGAR": 0.25
                }
            ),
            "London": DestinationMetrics(
                destination="London",
                total_searches=400,
                total_bookings=40,
                average_price=1300.0,
                popular_packages=[],  # Would contain actual packages
                seasonal_demand={
                    "Spring": 100,
                    "Summer": 150,
                    "Fall": 100,
                    "Winter": 50
                },
                provider_distribution={
                    "OLA": 0.3,
                    "AERO": 0.4,
                    "DESPEGAR": 0.3
                }
            )
        }

        sections = [
            ReportSection(
                title="Destination Overview",
                charts=[{
                    "type": "bar",
                    "title": "Destination Performance",
                    "data": {
                        "Searches": [m.total_searches for m in metrics.values()],
                        "Bookings": [m.total_bookings for m in metrics.values()]
                    }
                }]
            )
        ]

        # Add section for each destination
        for dest_metrics in metrics.values():
            sections.append(
                ReportSection(
                    title=f"{dest_metrics.destination} Analysis",
                    metrics=[
                        {
                            "name": "Conversion Rate",
                            "value": f"{dest_metrics.total_bookings / dest_metrics.total_searches:.1%}"
                        },
                        {
                            "name": "Average Price",
                            "value": f"${dest_metrics.average_price:.2f}"
                        }
                    ],
                    charts=[
                        {
                            "type": "line",
                            "title": "Seasonal Demand",
                            "data": dest_metrics.seasonal_demand
                        },
                        {
                            "type": "pie",
                            "title": "Provider Distribution",
                            "data": dest_metrics.provider_distribution
                        }
                    ]
                )
            )

        return sections

    def _generate_custom_sections(
        self,
        template: ReportTemplate,
        start_date: datetime,
        end_date: datetime
    ) -> List[ReportSection]:
        """Generate custom report sections from template."""
        sections = []
        for section_template in template.section_templates:
            # Here we would process the template and generate
            # appropriate sections based on the template logic
            sections.append(
                ReportSection(
                    title=section_template.get("title", "Custom Section"),
                    description=section_template.get("description")
                )
            )
        return sections

    @staticmethod
    def _get_report_title(type: ReportType, period: ReportPeriod) -> str:
        """Generate a title for the report."""
        return f"{type.title()} Report - {period.title()}"
