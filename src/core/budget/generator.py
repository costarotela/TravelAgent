"""Budget generator for travel packages."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from ..providers import TravelPackage
from .models import Budget, BudgetStatus, BudgetTemplate, BudgetVersion

logger = logging.getLogger(__name__)


class BudgetGenerator:
    """Generator for creating and managing travel budgets."""

    def __init__(self, default_markup: float = 0.15):
        """Initialize budget generator.
        
        Args:
            default_markup: Default markup percentage (0.15 = 15%)
        """
        self.default_markup = default_markup

    def create_budget(
        self,
        client_name: str,
        client_email: str,
        packages: List[TravelPackage],
        template: Optional[BudgetTemplate] = None,
        validity_days: Optional[int] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Budget:
        """Create a new budget from selected packages.
        
        Args:
            client_name: Name of the client
            client_email: Email of the client
            packages: List of travel packages to include
            template: Optional budget template to use
            validity_days: Optional number of days the budget is valid
            notes: Optional notes about the budget
            metadata: Optional metadata key-value pairs
        
        Returns:
            New Budget object
        """
        # Use template values or defaults
        markup = template.markup_percentage if template else self.default_markup
        valid_days = validity_days or (template.default_validity_days if template else 7)

        # Calculate prices
        total_price = sum(pkg.price for pkg in packages)
        final_price = total_price * (1 + markup)

        # Create initial version
        initial_version = BudgetVersion(
            version=1,
            created_by="system",
            comment="Initial budget creation",
            changes={},
            packages=packages,
            total_price=total_price,
            currency=packages[0].currency if packages else "USD",
            markup_percentage=markup,
            final_price=final_price
        )

        # Create budget
        budget = Budget(
            id=str(uuid4()),
            client_name=client_name,
            client_email=client_email,
            current_version=1,
            versions=[initial_version],
            valid_until=datetime.utcnow() + timedelta(days=valid_days),
            notes=notes,
            metadata=metadata or {}
        )

        logger.info(f"Created new budget {budget.id} for {client_name}")
        return budget

    def update_budget(
        self,
        budget: Budget,
        packages: Optional[List[TravelPackage]] = None,
        markup: Optional[float] = None,
        notes: Optional[str] = None,
        comment: str = "",
        created_by: str = "system"
    ) -> Budget:
        """Create a new version of an existing budget.
        
        Args:
            budget: Existing budget to update
            packages: Optional new list of packages
            markup: Optional new markup percentage
            notes: Optional new notes
            comment: Comment about the changes
            created_by: User or system creating the version
        
        Returns:
            Updated Budget object
        """
        if budget.status not in [BudgetStatus.DRAFT, BudgetStatus.PENDING]:
            raise ValueError(
                f"Cannot update budget in {budget.status} status"
            )

        # Get current version
        current = budget.versions[budget.current_version - 1]
        
        # Track changes
        changes = {}
        if packages:
            changes["packages"] = "Updated package selection"
        if markup is not None:
            changes["markup"] = f"Updated markup from {current.markup_percentage:.1%} to {markup:.1%}"
        if notes:
            changes["notes"] = "Updated notes"

        # Calculate new prices
        new_packages = packages or current.packages
        new_markup = markup if markup is not None else current.markup_percentage
        total_price = sum(pkg.price for pkg in new_packages)
        final_price = total_price * (1 + new_markup)

        # Create new version
        new_version = BudgetVersion(
            version=budget.current_version + 1,
            created_by=created_by,
            comment=comment,
            changes=changes,
            packages=new_packages,
            total_price=total_price,
            currency=new_packages[0].currency if new_packages else current.currency,
            markup_percentage=new_markup,
            final_price=final_price
        )

        # Update budget
        budget.versions.append(new_version)
        budget.current_version += 1
        budget.updated_at = datetime.utcnow()
        if notes:
            budget.notes = notes

        logger.info(
            f"Created version {budget.current_version} of budget {budget.id}"
        )
        return budget

    def update_status(
        self,
        budget: Budget,
        new_status: BudgetStatus,
        comment: str = "",
        created_by: str = "system"
    ) -> Budget:
        """Update the status of a budget.
        
        Args:
            budget: Budget to update
            new_status: New status to set
            comment: Comment about the status change
            created_by: User or system updating the status
        
        Returns:
            Updated Budget object
        """
        if new_status == budget.status:
            return budget

        # Validate status transition
        valid_transitions = {
            BudgetStatus.DRAFT: [
                BudgetStatus.PENDING,
                BudgetStatus.EXPIRED
            ],
            BudgetStatus.PENDING: [
                BudgetStatus.APPROVED,
                BudgetStatus.REJECTED,
                BudgetStatus.EXPIRED
            ],
            BudgetStatus.APPROVED: [
                BudgetStatus.EXPIRED
            ],
            BudgetStatus.REJECTED: [
                BudgetStatus.DRAFT
            ],
            BudgetStatus.EXPIRED: [
                BudgetStatus.DRAFT
            ]
        }

        if new_status not in valid_transitions[budget.status]:
            raise ValueError(
                f"Invalid status transition from {budget.status} to {new_status}"
            )

        # Create new version with status change
        current = budget.versions[budget.current_version - 1]
        new_version = BudgetVersion(
            version=budget.current_version + 1,
            created_by=created_by,
            comment=comment or f"Status changed to {new_status}",
            changes={"status": f"Changed from {budget.status} to {new_status}"},
            packages=current.packages,
            total_price=current.total_price,
            currency=current.currency,
            markup_percentage=current.markup_percentage,
            final_price=current.final_price
        )

        # Update budget
        budget.versions.append(new_version)
        budget.current_version += 1
        budget.status = new_status
        budget.updated_at = datetime.utcnow()

        logger.info(
            f"Updated budget {budget.id} status to {new_status}"
        )
        return budget

    def compare_versions(
        self,
        budget: Budget,
        version1: int,
        version2: int
    ) -> Dict[str, Dict]:
        """Compare two versions of a budget.
        
        Args:
            budget: Budget to compare versions from
            version1: First version number
            version2: Second version number
        
        Returns:
            Dictionary with differences between versions
        """
        if not (1 <= version1 <= len(budget.versions) and
                1 <= version2 <= len(budget.versions)):
            raise ValueError("Invalid version numbers")

        v1 = budget.versions[version1 - 1]
        v2 = budget.versions[version2 - 1]

        differences = {
            "packages": {
                "added": [
                    pkg for pkg in v2.packages
                    if pkg.id not in [p.id for p in v1.packages]
                ],
                "removed": [
                    pkg for pkg in v1.packages
                    if pkg.id not in [p.id for p in v2.packages]
                ]
            },
            "pricing": {
                "total_price_diff": v2.total_price - v1.total_price,
                "markup_diff": v2.markup_percentage - v1.markup_percentage,
                "final_price_diff": v2.final_price - v1.final_price
            },
            "metadata": {
                "created_by": v2.created_by,
                "comment": v2.comment,
                "changes": v2.changes
            }
        }

        return differences
