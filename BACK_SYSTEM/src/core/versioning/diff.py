"""Difference calculation and comparison utilities for budget versions."""

import logging
from typing import List, Dict, Any, Set
from deepdiff import DeepDiff

from .models import Change, ChangeType, VersionDiff

logger = logging.getLogger(__name__)


class DiffCalculator:
    """Calculator for version differences."""

    @staticmethod
    def calculate_diff(
        base_version: Dict[str, Any],
        target_version: Dict[str, Any],
    ) -> VersionDiff:
        """Calculate difference between two versions.

        Args:
            base_version: Base version data
            target_version: Target version data

        Returns:
            VersionDiff object with changes
        """
        # Usar DeepDiff para comparación profunda
        diff = DeepDiff(base_version, target_version, ignore_order=True)

        changes: List[Change] = []

        # Procesar cambios de valores
        for path, change in diff.get("values_changed", {}).items():
            field = path.replace("root['", "").replace("']", "")
            changes.append(
                Change(
                    id=f"change_{len(changes)}",
                    type=DiffCalculator._determine_change_type(field),
                    field=field,
                    old_value=change["old_value"],
                    new_value=change["new_value"],
                    author="system",
                    reason="Automatic diff detection",
                )
            )

        # Procesar elementos agregados
        for path, value in diff.get("dictionary_item_added", {}).items():
            field = path.replace("root['", "").replace("']", "")
            changes.append(
                Change(
                    id=f"change_{len(changes)}",
                    type=DiffCalculator._determine_change_type(field),
                    field=field,
                    old_value=None,
                    new_value=value,
                    author="system",
                    reason="Item added",
                )
            )

        # Procesar elementos eliminados
        for path, value in diff.get("dictionary_item_removed", {}).items():
            field = path.replace("root['", "").replace("']", "")
            changes.append(
                Change(
                    id=f"change_{len(changes)}",
                    type=DiffCalculator._determine_change_type(field),
                    field=field,
                    old_value=value,
                    new_value=None,
                    author="system",
                    reason="Item removed",
                )
            )

        return VersionDiff(
            base_version_id=base_version["id"],
            target_version_id=target_version["id"],
            changes=changes,
            summary=DiffCalculator._create_summary(changes),
        )

    @staticmethod
    def _determine_change_type(field: str) -> ChangeType:
        """Determine type of change based on field name."""
        field_lower = field.lower()

        if "price" in field_lower or "cost" in field_lower:
            return ChangeType.PRICE
        elif "package" in field_lower or "service" in field_lower:
            return ChangeType.PACKAGE
        elif "margin" in field_lower:
            return ChangeType.MARGIN
        elif "discount" in field_lower:
            return ChangeType.DISCOUNT
        elif "rule" in field_lower:
            return ChangeType.RULE
        elif "preference" in field_lower:
            return ChangeType.PREFERENCE
        else:
            return ChangeType.METADATA

    @staticmethod
    def _create_summary(changes: List[Change]) -> Dict[str, Any]:
        """Create a summary of changes."""
        summary = {
            "total_changes": len(changes),
            "changes_by_type": {},
            "significant_changes": [],
        }

        # Contar cambios por tipo
        for change in changes:
            if change.type not in summary["changes_by_type"]:
                summary["changes_by_type"][change.type] = 0
            summary["changes_by_type"][change.type] += 1

            # Identificar cambios significativos
            if DiffCalculator._is_significant_change(change):
                summary["significant_changes"].append(
                    {
                        "field": change.field,
                        "type": change.type,
                        "old_value": change.old_value,
                        "new_value": change.new_value,
                    }
                )

        return summary

    @staticmethod
    def _is_significant_change(change: Change) -> bool:
        """Determine if a change is significant."""
        if change.type in [ChangeType.PRICE, ChangeType.MARGIN]:
            # Cambios de precio o margen mayores al 5%
            try:
                old_val = float(change.old_value or 0)
                new_val = float(change.new_value or 0)
                if old_val > 0:
                    return abs((new_val - old_val) / old_val) > 0.05
            except (ValueError, TypeError):
                pass

        elif change.type == ChangeType.PACKAGE:
            # Cualquier cambio en paquetes es significativo
            return True

        elif change.type == ChangeType.RULE:
            # Cambios en reglas son significativos
            return True

        return False


class ConflictResolver:
    """Resolver for version conflicts."""

    @staticmethod
    def detect_conflicts(
        base_changes: List[Change],
        branch_changes: List[Change],
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between two sets of changes.

        Args:
            base_changes: Changes from base version
            branch_changes: Changes from branch version

        Returns:
            List of conflicts
        """
        conflicts = []

        # Agrupar cambios por campo
        base_by_field = {c.field: c for c in base_changes}
        branch_by_field = {c.field: c for c in branch_changes}

        # Encontrar campos modificados en ambas versiones
        common_fields = set(base_by_field.keys()) & set(branch_by_field.keys())

        for field in common_fields:
            base_change = base_by_field[field]
            branch_change = branch_by_field[field]

            # Si los cambios son diferentes, hay conflicto
            if base_change.new_value != branch_change.new_value:
                conflicts.append(
                    {
                        "field": field,
                        "type": base_change.type,
                        "base_value": base_change.new_value,
                        "branch_value": branch_change.new_value,
                        "resolution_options": ConflictResolver._get_resolution_options(
                            base_change, branch_change
                        ),
                    }
                )

        return conflicts

    @staticmethod
    def _get_resolution_options(
        base_change: Change,
        branch_change: Change,
    ) -> List[Dict[str, Any]]:
        """Get possible resolution options for a conflict."""
        options = [
            {
                "strategy": "base",
                "value": base_change.new_value,
                "description": "Keep base version value",
            },
            {
                "strategy": "branch",
                "value": branch_change.new_value,
                "description": "Keep branch version value",
            },
        ]

        # Para cambios numéricos, ofrecer promedio
        try:
            base_val = float(base_change.new_value)
            branch_val = float(branch_change.new_value)
            average = (base_val + branch_val) / 2
            options.append(
                {
                    "strategy": "average",
                    "value": average,
                    "description": "Use average of both values",
                }
            )
        except (ValueError, TypeError):
            pass

        return options
