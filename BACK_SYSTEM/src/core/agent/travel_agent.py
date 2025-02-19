"""Travel agent implementation."""

from typing import List, Optional, Dict
from datetime import datetime

from src.core.agent.base import AgentCore
from src.core.providers.base import SearchCriteria, TravelPackage
from src.core.notifications.manager import NotificationManager
from src.core.notifications.change_notifier import ChangeNotifier
from src.core.notifications.providers import EmailProvider, WebhookProvider


class TravelAgent(AgentCore):
    """Simple travel agent with basic functionality."""

    def __init__(self):
        """Initialize travel agent with notification system."""
        super().__init__()

        # Configuración de notificaciones
        email_config = {
            "smtp_host": "smtp.tuempresa.com",
            "smtp_port": 587,
            "username": "notificaciones@tuempresa.com",
            "password": "tupassword",
            "use_tls": True,
            "from_email": "notificaciones@tuempresa.com",
        }

        webhook_config = {
            "webhook_url": "https://hooks.slack.com/services/XXXX/XXXX/XXXX",
            "secret_key": "your-secret-key",
        }

        # Inicializar proveedores de notificaciones
        email_provider = EmailProvider(**email_config)
        webhook_provider = WebhookProvider(**webhook_config)

        # Inicializar manager de notificaciones
        self.notification_manager = NotificationManager(
            email_provider=email_provider,
            webhook_provider=webhook_provider,
        )

        # Inicializar notificador de cambios
        self.change_notifier = ChangeNotifier(
            notification_manager=self.notification_manager,
            threshold=5,
            recipients=["alertas@tuempresa.com"],
        )

    async def search_packages(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for travel packages."""
        await self.start_action("search_packages")

        try:
            # Simulated search for now
            packages = [
                TravelPackage(
                    id="pkg1",
                    provider="test",
                    origin=criteria.origin,
                    destination=criteria.destination,
                    departure_date=criteria.departure_date,
                    return_date=criteria.return_date,
                    price=1000.0,
                    currency="USD",
                    availability=10,
                    details={"flight": "AA123"},
                )
            ]

            # Track metrics
            await self.add_metric("results_count", len(packages))
            await self.add_metric("search_time_ms", 100)

            await self.end_action(success=True)
            return packages

        except Exception as e:
            await self.end_action(success=False, error=str(e))
            raise

    async def analyze_prices(self, packages: List[TravelPackage]) -> dict:
        """Basic price analysis."""
        await self.start_action("analyze_prices")

        try:
            prices = [p.price for p in packages]
            analysis = {
                "min_price": min(prices) if prices else 0,
                "max_price": max(prices) if prices else 0,
                "avg_price": sum(prices) / len(prices) if prices else 0,
            }

            await self.add_metric("packages_analyzed", len(packages))

            await self.end_action(success=True)
            return analysis

        except Exception as e:
            await self.end_action(success=False, error=str(e))
            raise

    async def update_ola_data(self, destino: str) -> None:
        """Update OLA data and process changes.

        Args:
            destino: Destination to update data for
        """
        await self.start_action("update_ola_data")

        try:
            # Obtener datos actualizados (simulado por ahora)
            report = {
                "stats": {
                    "total_nuevos": 3,
                    "total_actualizados": 2,
                    "total_eliminados": 1,
                },
                "nuevos": [
                    {"id": "pkg1", "destino": destino, "precio": 1000},
                    {"id": "pkg2", "destino": destino, "precio": 1200},
                    {"id": "pkg3", "destino": destino, "precio": 800},
                ],
                "actualizados": [
                    {
                        "id": "pkg4",
                        "destino": destino,
                        "precio_anterior": 900,
                        "precio_nuevo": 950,
                    },
                    {
                        "id": "pkg5",
                        "destino": destino,
                        "precio_anterior": 1100,
                        "precio_nuevo": 1050,
                    },
                ],
                "eliminados": [
                    {"id": "pkg6", "destino": destino, "ultimo_precio": 1300},
                ],
            }

            # Procesar cambios y enviar notificaciones
            self.change_notifier.process_report(report)

            # Track metrics
            await self.add_metric("packages_updated", len(report["actualizados"]))
            await self.add_metric("packages_added", len(report["nuevos"]))
            await self.add_metric("packages_removed", len(report["eliminados"]))

            await self.end_action(success=True)

        except Exception as e:
            await self.end_action(success=False, error=str(e))
            raise

    def get_performance_summary(self) -> dict:
        """Get basic performance metrics."""
        return {
            "search_success_rate": self.get_success_rate("search_packages"),
            "analysis_success_rate": self.get_success_rate("analyze_prices"),
            "recent_metrics": self.get_recent_metrics(),
        }
