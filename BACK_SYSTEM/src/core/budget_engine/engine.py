"""Budget update engine implementation."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4
from prometheus_client import Counter, Histogram

from .models import Budget, BudgetVersion, BudgetRule, BudgetChange
from .rules import RuleEngine
from ..collectors.models import PackageData
from ..notifications import NotificationManager
from ..monitoring import METRICS

logger = logging.getLogger(__name__)

# Initialize metrics
METRICS["budget_updates"] = Counter(
    "budget_updates_total",
    "Total number of budget updates",
    ["status", "change_type"],
)
METRICS["budget_processing_time"] = Histogram(
    "budget_processing_seconds",
    "Time taken to process budget updates",
)
METRICS["rule_applications"] = Counter(
    "rule_applications_total",
    "Number of times each rule was applied",
    ["rule_name"],
)


class BudgetUpdateEngine:
    """Engine for updating travel budgets based on package changes."""

    def __init__(
        self,
        rules: Optional[List[BudgetRule]] = None,
        notification_manager: Optional[NotificationManager] = None,
    ):
        """Initialize budget update engine.

        Args:
            rules: Optional list of business rules
            notification_manager: Optional notification manager
        """
        self.rule_engine = RuleEngine(rules)
        self.notification_manager = notification_manager

    def create_budget(
        self,
        client_name: str,
        client_email: str,
        packages: List[PackageData],
        markup_percentage: float = 0.15,
        valid_days: int = 7,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Budget:
        """Create a new budget from package data.

        Args:
            client_name: Name of the client
            client_email: Email of the client
            packages: List of travel packages
            markup_percentage: Markup percentage (0.15 = 15%)
            valid_days: Number of days the budget is valid
            notes: Optional notes about the budget
            metadata: Optional metadata

        Returns:
            New Budget object
        """
        # Create initial version
        initial_version = BudgetVersion(
            version=1,
            packages=packages,
            total_price=sum(p.price for p in packages),
            currency=packages[0].currency if packages else "USD",
            markup_percentage=markup_percentage,
            final_price=sum(p.price for p in packages) * (1 + markup_percentage),
        )

        # Create budget
        budget = Budget(
            id=str(uuid4()),
            client_name=client_name,
            client_email=client_email,
            current_version=1,
            versions=[initial_version],
            valid_until=datetime.utcnow() + datetime.timedelta(days=valid_days),
            notes=notes,
            metadata=metadata or {},
        )

        logger.info(f"Created new budget {budget.id} for {client_name}")
        return budget

    def update_budget(
        self,
        budget: Budget,
        new_packages: List[PackageData],
    ) -> Budget:
        """Update a budget with new package data.

        Args:
            budget: Existing budget to update
            new_packages: New package data

        Returns:
            Updated Budget object
        """
        start_time = datetime.utcnow()

        try:
            # Map current packages by ID
            current_packages = {p.package_id: p for p in budget.current.packages}

            # Detect all changes
            changes = []
            for new_pkg in new_packages:
                if old_pkg := current_packages.get(new_pkg.package_id):
                    # Package exists, check for changes
                    pkg_changes = self.rule_engine.evaluate_changes(old_pkg, new_pkg)
                    changes.extend(pkg_changes)
                else:
                    # New package
                    changes.append(
                        BudgetChange(
                            change_type=ChangeType.PACKAGE_ADDED,
                            old_value=None,
                            new_value=new_pkg.dict(),
                            package_id=new_pkg.package_id,
                            provider=new_pkg.provider,
                        )
                    )

            # Check for removed packages
            for pkg_id in current_packages:
                if pkg_id not in {p.package_id for p in new_packages}:
                    changes.append(
                        BudgetChange(
                            change_type=ChangeType.PACKAGE_REMOVED,
                            old_value=current_packages[pkg_id].dict(),
                            new_value=None,
                            package_id=pkg_id,
                            provider=current_packages[pkg_id].provider,
                        )
                    )

            if changes:
                # Apply business rules
                new_version = self.rule_engine.apply_rules(budget, changes)

                # Update budget
                budget.versions.append(new_version)
                budget.current_version += 1
                budget.updated_at = datetime.utcnow()

                # Send notifications if significant changes
                if self.notification_manager:
                    self._send_notifications(budget, changes)

                # Update metrics
                for change in changes:
                    METRICS["budget_updates"].labels(
                        status="success",
                        change_type=change.change_type,
                    ).inc()

                logger.info(
                    f"Updated budget {budget.id} to version {budget.current_version}"
                )
            else:
                logger.info(f"No changes detected for budget {budget.id}")

        except Exception as e:
            logger.error(f"Error updating budget {budget.id}: {str(e)}")
            METRICS["budget_updates"].labels(
                status="error",
                change_type="error",
            ).inc()
            raise

        finally:
            # Record processing time
            duration = (datetime.utcnow() - start_time).total_seconds()
            METRICS["budget_processing_time"].observe(duration)

        return budget

    def _send_notifications(self, budget: Budget, changes: List[BudgetChange]) -> None:
        """Send notifications for significant changes.

        Args:
            budget: Updated budget
            changes: List of changes
        """
        if not self.notification_manager:
            return

        significant_changes = []
        for change in changes:
            if change.change_type in [
                ChangeType.PRICE_INCREASE,
                ChangeType.PRICE_DECREASE,
            ]:
                if abs(change.metadata.get("price_diff_percent", 0)) > 5:
                    significant_changes.append(change)
            elif change.change_type in [
                ChangeType.PACKAGE_REMOVED,
                ChangeType.AVAILABILITY_CHANGE,
            ]:
                significant_changes.append(change)

        if significant_changes:
            self.notification_manager.send_notification(
                recipient=budget.client_email,
                subject=f"Important changes to your travel budget {budget.id}",
                content=self._format_change_notification(budget, significant_changes),
            )
