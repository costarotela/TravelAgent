"""Preference management system implementation."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from prometheus_client import Counter, Histogram

from .models import (
    PreferenceType,
    PreferenceValue,
    UserPreferences,
    VendorRule,
    FilterConfig,
)
from ..monitoring import METRICS

logger = logging.getLogger(__name__)

# Initialize metrics
METRICS["preference_updates"] = Counter(
    "preference_updates_total",
    "Total number of preference updates",
    ["preference_type", "source"],
)
METRICS["preference_processing_time"] = Histogram(
    "preference_processing_seconds",
    "Time taken to process preference updates",
)


class PreferenceManager:
    """Manager for user and vendor preferences."""

    def __init__(self, storage_backend: Optional[Any] = None):
        """Initialize preference manager.

        Args:
            storage_backend: Optional backend for storing preferences
        """
        self.storage = storage_backend
        self.vendor_rules: List[VendorRule] = []
        self.filter_configs: Dict[str, FilterConfig] = {}

    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """Get preferences for a user.

        Args:
            user_id: ID of the user

        Returns:
            User preferences
        """
        if self.storage:
            prefs = await self.storage.get_preferences(user_id)
            if prefs:
                return UserPreferences.parse_obj(prefs)

        # Return default preferences if none found
        return UserPreferences(
            user_id=user_id,
            preferences={ptype: {} for ptype in PreferenceType},
        )

    async def set_preference(
        self,
        user_id: str,
        pref_type: PreferenceType,
        key: str,
        value: Any,
        source: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserPreferences:
        """Set a preference value for a user.

        Args:
            user_id: ID of the user
            pref_type: Type of preference
            key: Preference key
            value: Preference value
            source: Source of the preference
            metadata: Optional metadata

        Returns:
            Updated user preferences
        """
        start_time = datetime.utcnow()

        try:
            # Get current preferences
            prefs = await self.get_user_preferences(user_id)

            # Create preference value
            pref_value = PreferenceValue(
                value=value,
                source=source,
                metadata=metadata or {},
            )

            # Update preferences
            if pref_type not in prefs.preferences:
                prefs.preferences[pref_type] = {}
            prefs.preferences[pref_type][key] = pref_value
            prefs.updated_at = datetime.utcnow()

            # Store preferences
            if self.storage:
                await self.storage.save_preferences(user_id, prefs.dict())

            # Update metrics
            METRICS["preference_updates"].labels(
                preference_type=pref_type,
                source=source,
            ).inc()

            logger.info(
                f"Updated preference {pref_type}.{key} for user {user_id}"
            )
            return prefs

        finally:
            # Record processing time
            duration = (datetime.utcnow() - start_time).total_seconds()
            METRICS["preference_processing_time"].observe(duration)

    def add_vendor_rule(self, rule: VendorRule) -> None:
        """Add a vendor rule.

        Args:
            rule: Vendor rule to add
        """
        self.vendor_rules.append(rule)
        self.vendor_rules.sort(key=lambda x: x.priority, reverse=True)
        logger.info(f"Added vendor rule: {rule.name}")

    def add_filter_config(self, config: FilterConfig) -> None:
        """Add a filter configuration.

        Args:
            config: Filter configuration to add
        """
        self.filter_configs[config.name] = config
        logger.info(f"Added filter config: {config.name}")

    async def apply_vendor_rules(
        self, user_id: str, context: Dict[str, Any]
    ) -> UserPreferences:
        """Apply vendor rules to user preferences.

        Args:
            user_id: ID of the user
            context: Context for rule evaluation

        Returns:
            Updated user preferences
        """
        prefs = await self.get_user_preferences(user_id)

        for rule in self.vendor_rules:
            if not rule.enabled:
                continue

            try:
                if self._evaluate_rule_conditions(rule, context):
                    # Apply rule actions
                    for action, params in rule.actions.items():
                        if action == "set_preference":
                            await self.set_preference(
                                user_id=user_id,
                                pref_type=rule.preference_type,
                                key=params["key"],
                                value=params["value"],
                                source="vendor_rule",
                                metadata={"rule": rule.name},
                            )
            except Exception as e:
                logger.error(f"Error applying vendor rule {rule.name}: {str(e)}")

        return prefs

    def apply_filters(
        self, data: List[Dict[str, Any]], user_id: str
    ) -> List[Dict[str, Any]]:
        """Apply filters to data based on user preferences.

        Args:
            data: Data to filter
            user_id: ID of the user

        Returns:
            Filtered data
        """
        filtered_data = data

        for config in self.filter_configs.values():
            if not config.enabled:
                continue

            try:
                filtered_data = self._apply_filter(
                    filtered_data, config, user_id
                )
            except Exception as e:
                logger.error(
                    f"Error applying filter {config.name}: {str(e)}"
                )

        return filtered_data

    def _evaluate_rule_conditions(
        self, rule: VendorRule, context: Dict[str, Any]
    ) -> bool:
        """Evaluate conditions for a vendor rule.

        Args:
            rule: Rule to evaluate
            context: Context for evaluation

        Returns:
            True if conditions are met
        """
        try:
            for key, value in rule.conditions.items():
                if key not in context:
                    return False
                if context[key] != value:
                    return False
            return True
        except Exception as e:
            logger.error(
                f"Error evaluating conditions for rule {rule.name}: {str(e)}"
            )
            return False

    def _apply_filter(
        self,
        data: List[Dict[str, Any]],
        config: FilterConfig,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Apply a single filter configuration.

        Args:
            data: Data to filter
            config: Filter configuration
            user_id: ID of the user

        Returns:
            Filtered data
        """
        if config.filter_type == "price":
            min_price = config.criteria.get("min")
            max_price = config.criteria.get("max")
            if min_price is not None:
                data = [
                    item for item in data
                    if item.get("price", 0) >= min_price
                ]
            if max_price is not None:
                data = [
                    item for item in data
                    if item.get("price", 0) <= max_price
                ]

        elif config.filter_type == "date":
            start_date = config.criteria.get("start")
            end_date = config.criteria.get("end")
            if start_date and end_date:
                data = [
                    item for item in data
                    if start_date <= item.get("date", "") <= end_date
                ]

        elif config.filter_type == "destination":
            destinations = config.criteria.get("destinations", [])
            if destinations:
                data = [
                    item for item in data
                    if item.get("destination") in destinations
                ]

        return data
