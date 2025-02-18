"""Business rules for budget updates."""

import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from .models import BudgetRule, BudgetChange, ChangeType, Budget, BudgetVersion
from ..collectors.models import PackageData

logger = logging.getLogger(__name__)


class RuleEngine:
    """Engine for applying business rules to budgets."""

    def __init__(self, rules: Optional[List[BudgetRule]] = None):
        """Initialize rule engine with optional rules."""
        self.rules = sorted(rules or [], key=lambda x: x.priority, reverse=True)

    def evaluate_changes(
        self, old_package: PackageData, new_package: PackageData
    ) -> List[BudgetChange]:
        """Evaluate changes between old and new package data.

        Args:
            old_package: Previous package data
            new_package: New package data

        Returns:
            List of detected changes
        """
        changes = []

        # Check price changes
        if old_package.price != new_package.price:
            change_type = (
                ChangeType.PRICE_INCREASE
                if new_package.price > old_package.price
                else ChangeType.PRICE_DECREASE
            )
            changes.append(
                BudgetChange(
                    change_type=change_type,
                    old_value=old_package.price,
                    new_value=new_package.price,
                    package_id=new_package.package_id,
                    provider=new_package.provider,
                    metadata={
                        "price_diff": float(new_package.price - old_package.price),
                        "price_diff_percent": float(
                            (new_package.price - old_package.price)
                            / old_package.price
                            * 100
                        ),
                    },
                )
            )

        # Check availability changes
        if old_package.availability != new_package.availability:
            changes.append(
                BudgetChange(
                    change_type=ChangeType.AVAILABILITY_CHANGE,
                    old_value=old_package.availability,
                    new_value=new_package.availability,
                    package_id=new_package.package_id,
                    provider=new_package.provider,
                )
            )

        # Check dates changes
        if old_package.dates != new_package.dates:
            changes.append(
                BudgetChange(
                    change_type=ChangeType.DATES_CHANGE,
                    old_value=[d.isoformat() for d in old_package.dates],
                    new_value=[d.isoformat() for d in new_package.dates],
                    package_id=new_package.package_id,
                    provider=new_package.provider,
                )
            )

        # Check details changes
        if old_package.details != new_package.details:
            changes.append(
                BudgetChange(
                    change_type=ChangeType.DETAILS_CHANGE,
                    old_value=old_package.details,
                    new_value=new_package.details,
                    package_id=new_package.package_id,
                    provider=new_package.provider,
                )
            )

        return changes

    def apply_rules(
        self, budget: Budget, changes: List[BudgetChange]
    ) -> BudgetVersion:
        """Apply business rules based on detected changes.

        Args:
            budget: Current budget
            changes: List of detected changes

        Returns:
            New budget version with applied rules
        """
        current = budget.current
        new_version = BudgetVersion(
            version=budget.current_version + 1,
            packages=current.packages.copy(),
            total_price=current.total_price,
            currency=current.currency,
            markup_percentage=current.markup_percentage,
            final_price=current.final_price,
            changes=changes,
        )

        # Apply rules in priority order
        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                if self._evaluate_rule_condition(rule, changes):
                    new_version = self._apply_rule_action(rule, new_version)
                    # Mark rule as applied in changes
                    for change in changes:
                        change.applied_rules.append(rule.name)
            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {str(e)}")

        # Recalculate final prices
        new_version.total_price = sum(
            Decimal(str(p.price)) for p in new_version.packages
        )
        new_version.final_price = new_version.total_price * Decimal(
            str(1 + new_version.markup_percentage)
        )

        return new_version

    def _evaluate_rule_condition(
        self, rule: BudgetRule, changes: List[BudgetChange]
    ) -> bool:
        """Evaluate if a rule's condition is met.

        Args:
            rule: Rule to evaluate
            changes: List of changes to check against

        Returns:
            True if condition is met
        """
        condition = rule.condition
        condition_type = condition.get("type")

        if condition_type == "price_increase":
            threshold = condition.get("threshold", 0)
            for change in changes:
                if (
                    change.change_type == ChangeType.PRICE_INCREASE
                    and change.metadata.get("price_diff_percent", 0) > threshold
                ):
                    return True

        elif condition_type == "price_decrease":
            threshold = condition.get("threshold", 0)
            for change in changes:
                if (
                    change.change_type == ChangeType.PRICE_DECREASE
                    and abs(change.metadata.get("price_diff_percent", 0)) > threshold
                ):
                    return True

        elif condition_type == "availability_low":
            threshold = condition.get("threshold", 0)
            for change in changes:
                if (
                    change.change_type == ChangeType.AVAILABILITY_CHANGE
                    and change.new_value < threshold
                ):
                    return True

        return False

    def _apply_rule_action(
        self, rule: BudgetRule, version: BudgetVersion
    ) -> BudgetVersion:
        """Apply a rule's action to the budget version.

        Args:
            rule: Rule to apply
            version: Budget version to modify

        Returns:
            Modified budget version
        """
        action = rule.action
        action_type = action.get("type")

        if action_type == "apply_discount":
            discount = Decimal(str(action.get("value", 0) / 100))
            for package in version.packages:
                package.price = package.price * (1 - discount)

        elif action_type == "increase_markup":
            increase = action.get("value", 0) / 100
            version.markup_percentage += increase

        elif action_type == "decrease_markup":
            decrease = action.get("value", 0) / 100
            version.markup_percentage = max(0, version.markup_percentage - decrease)

        return version
