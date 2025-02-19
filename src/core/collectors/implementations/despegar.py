"""Despegar provider implementation."""

import logging
from datetime import datetime
from typing import List
import json

from ..models import PackageData, ProviderConfig
from ..providers import BaseProviderUpdater

logger = logging.getLogger(__name__)


class DespegarProviderUpdater(BaseProviderUpdater):
    """Implementation for Despegar provider."""

    async def _fetch_raw_data(self, destination: str) -> List[dict]:
        """Fetch raw data from Despegar.

        Args:
            destination: Destination to fetch data for

        Returns:
            List of raw package data
        """
        try:
            # Navigate to search page
            url = f"{self.config.base_url}/paquetes?destino={destination}"
            await self.browser.navigate(url)

            # Wait for packages to load
            await self.browser.wait_for_element(".package-card", timeout=10)

            # Extract data
            script = """
            () => {
                const packages = [];
                document.querySelectorAll('.package-card').forEach(pkg => {
                    packages.push({
                        id: pkg.getAttribute('data-product-id'),
                        title: pkg.querySelector('.product-title').textContent,
                        price: pkg.querySelector('.price-amount').textContent,
                        currency: pkg.querySelector('.price-currency').textContent,
                        departure: pkg.querySelector('.departure-date').textContent,
                        return: pkg.querySelector('.return-date').textContent,
                        availability: parseInt(pkg.querySelector('.rooms-left').textContent),
                        details: {
                            hotel: {
                                name: pkg.querySelector('.hotel-name').textContent,
                                stars: pkg.querySelector('.hotel-stars').textContent,
                                address: pkg.querySelector('.hotel-address').textContent
                            },
                            flight: {
                                airline: pkg.querySelector('.airline').textContent,
                                duration: pkg.querySelector('.flight-duration').textContent
                            }
                        }
                    });
                });
                return packages;
            }
            """
            raw_data = await self.browser.execute_script(script)

            # Log success
            logger.info(
                f"Successfully fetched {len(raw_data)} packages from Despegar for {destination}"
            )

            return raw_data

        except Exception as e:
            logger.error(f"Error fetching data from Despegar: {str(e)}")
            raise

    def _normalize_data(self, raw_data: List[dict]) -> List[PackageData]:
        """Normalize Despegar data to common format.

        Args:
            raw_data: Raw data from Despegar

        Returns:
            List of normalized package data
        """
        normalized = []
        for item in raw_data:
            try:
                # Parse dates
                dates = []
                for date_field in ["departure", "return"]:
                    if date_str := item.get(date_field):
                        try:
                            date = datetime.strptime(date_str.strip(), "%d/%m/%Y")
                            dates.append(date)
                        except ValueError:
                            logger.warning(f"Could not parse date: {date_str}")

                # Parse price
                price_str = item.get("price", "0").replace(".", "").replace(",", ".")
                price = float(price_str)

                # Create normalized package
                package = PackageData(
                    provider="Despegar",
                    destination=item.get("title", "").split(",")[0],
                    price=price,
                    currency=item.get("currency", "USD"),
                    dates=sorted(dates),
                    availability=item.get("availability", 0),
                    package_id=item.get("id", ""),
                    details={
                        "hotel": item.get("details", {}).get("hotel", {}),
                        "flight": item.get("details", {}).get("flight", {}),
                    },
                    metadata={
                        "raw_title": item.get("title"),
                        "source": "web_scraping",
                    },
                )
                normalized.append(package)

            except Exception as e:
                logger.error(f"Error normalizing Despegar package: {str(e)}")
                continue

        return normalized
