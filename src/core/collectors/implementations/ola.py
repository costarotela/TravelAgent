"""OLA provider implementation."""

import logging
from datetime import datetime
from typing import List
import json

from ..models import PackageData, ProviderConfig
from ..providers import BaseProviderUpdater

logger = logging.getLogger(__name__)


class OLAProviderUpdater(BaseProviderUpdater):
    """Implementation for OLA provider."""

    async def _fetch_raw_data(self, destination: str) -> List[dict]:
        """Fetch raw data from OLA.

        Args:
            destination: Destination to fetch data for

        Returns:
            List of raw package data
        """
        try:
            # Navigate to search page
            url = f"{self.config.base_url}/busqueda?destino={destination}"
            await self.browser.navigate(url)
            
            # Wait for packages to load
            await self.browser.wait_for_element(".ola-package", timeout=10)
            
            # Extract data
            script = """
            () => {
                const packages = [];
                document.querySelectorAll('.ola-package').forEach(pkg => {
                    packages.push({
                        id: pkg.getAttribute('data-package-id'),
                        title: pkg.querySelector('.title').textContent,
                        price: pkg.querySelector('.price').textContent,
                        currency: pkg.querySelector('.currency').textContent,
                        dates: Array.from(pkg.querySelectorAll('.date')).map(d => d.textContent),
                        availability: parseInt(pkg.querySelector('.availability').textContent),
                        details: {
                            hotel: pkg.querySelector('.hotel').textContent,
                            flight: pkg.querySelector('.flight').textContent,
                            amenities: Array.from(pkg.querySelectorAll('.amenity')).map(a => a.textContent)
                        }
                    });
                });
                return packages;
            }
            """
            raw_data = await self.browser.execute_script(script)
            
            # Log success
            logger.info(
                f"Successfully fetched {len(raw_data)} packages from OLA for {destination}"
            )
            
            return raw_data

        except Exception as e:
            logger.error(f"Error fetching data from OLA: {str(e)}")
            raise

    def _normalize_data(self, raw_data: List[dict]) -> List[PackageData]:
        """Normalize OLA data to common format.

        Args:
            raw_data: Raw data from OLA

        Returns:
            List of normalized package data
        """
        normalized = []
        for item in raw_data:
            try:
                # Parse dates
                dates = [
                    datetime.strptime(date.strip(), "%d/%m/%Y")
                    for date in item.get("dates", [])
                ]
                
                # Parse price (remove currency symbol and convert to float)
                price_str = item.get("price", "0").replace("$", "").replace(",", "")
                price = float(price_str)
                
                # Create normalized package
                package = PackageData(
                    provider="OLA",
                    destination=item.get("title", "").split(" - ")[-1],
                    price=price,
                    currency=item.get("currency", "USD"),
                    dates=dates,
                    availability=item.get("availability", 0),
                    package_id=item.get("id", ""),
                    details=item.get("details", {}),
                    metadata={
                        "raw_title": item.get("title"),
                        "source": "web_scraping",
                    },
                )
                normalized.append(package)
                
            except Exception as e:
                logger.error(f"Error normalizing OLA package: {str(e)}")
                continue
        
        return normalized
