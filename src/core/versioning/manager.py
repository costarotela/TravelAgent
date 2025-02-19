"""Version management system implementation."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from prometheus_client import Counter, Histogram
import networkx as nx

from .models import (
    ChangeType,
    ChangeStatus,
    Change,
    Version,
    Branch,
    MergeStrategy,
    MergeResult,
    VersionDiff,
    VersionGraph,
)
from ..monitoring import METRICS

logger = logging.getLogger(__name__)

# Initialize metrics
METRICS["version_operations"] = Counter(
    "version_operations_total",
    "Total number of version operations",
    ["operation_type"],
)
METRICS["version_processing_time"] = Histogram(
    "version_processing_seconds",
    "Time taken to process version operations",
)


class VersionManager:
    """Manager for budget versions."""

    def __init__(self, storage_backend: Optional[Any] = None):
        """Initialize version manager.

        Args:
            storage_backend: Optional backend for storing versions
        """
        self.storage = storage_backend
        self.version_cache: Dict[str, Version] = {}
        self.branch_cache: Dict[str, Branch] = {}

    async def create_version(
        self,
        budget_id: str,
        name: str,
        changes: List[Change],
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
        author: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Version:
        """Create a new version.

        Args:
            budget_id: ID of the budget
            name: Name of the version
            changes: List of changes
            parent_id: Optional ID of parent version
            description: Optional description
            author: Author of the version
            metadata: Optional metadata

        Returns:
            Created version
        """
        start_time = datetime.utcnow()

        try:
            # Get next version number
            number = await self._get_next_version_number(budget_id)

            # Create version
            version = Version(
                id=f"{budget_id}_v{number}",
                budget_id=budget_id,
                number=number,
                parent_id=parent_id,
                name=name,
                description=description,
                changes=changes,
                created_by=author,
                metadata=metadata or {},
            )

            # Store version
            if self.storage:
                await self.storage.save_version(version.dict())
            self.version_cache[version.id] = version

            # Update metrics
            METRICS["version_operations"].labels(operation_type="create").inc()

            return version

        finally:
            # Record processing time
            duration = (datetime.utcnow() - start_time).total_seconds()
            METRICS["version_processing_time"].observe(duration)

    async def create_branch(
        self,
        budget_id: str,
        name: str,
        base_version_id: str,
        description: Optional[str] = None,
        author: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Branch:
        """Create a new branch.

        Args:
            budget_id: ID of the budget
            name: Name of the branch
            base_version_id: ID of base version
            description: Optional description
            author: Author of the branch
            metadata: Optional metadata

        Returns:
            Created branch
        """
        branch = Branch(
            id=f"{budget_id}_b_{name.lower()}",
            budget_id=budget_id,
            name=name,
            description=description,
            base_version_id=base_version_id,
            versions=[base_version_id],
            created_by=author,
            metadata=metadata or {},
        )

        # Store branch
        if self.storage:
            await self.storage.save_branch(branch.dict())
        self.branch_cache[branch.id] = branch

        # Update metrics
        METRICS["version_operations"].labels(operation_type="create_branch").inc()

        return branch

    async def merge_versions(
        self,
        source_version_id: str,
        target_version_id: str,
        strategy: MergeStrategy = MergeStrategy.MANUAL,
        author: str = "system",
    ) -> MergeResult:
        """Merge two versions.

        Args:
            source_version_id: ID of source version
            target_version_id: ID of target version
            strategy: Merge strategy
            author: Author of the merge

        Returns:
            Merge result
        """
        start_time = datetime.utcnow()

        try:
            # Get versions
            source = await self.get_version(source_version_id)
            target = await self.get_version(target_version_id)

            if not source or not target:
                return MergeResult(
                    success=False, metadata={"error": "Version not found"}
                )

            # Get changes since common ancestor
            ancestor_id = await self._find_common_ancestor(
                source_version_id, target_version_id
            )
            source_changes = await self._get_changes_since(
                source_version_id, ancestor_id
            )
            target_changes = await self._get_changes_since(
                target_version_id, ancestor_id
            )

            # Find conflicts
            conflicts = self._find_conflicts(source_changes, target_changes)

            # If there are conflicts and strategy is manual, return them
            if conflicts and strategy == MergeStrategy.MANUAL:
                return MergeResult(
                    success=False,
                    conflicts=conflicts,
                    metadata={"status": "conflicts_detected"},
                )

            # Apply merge strategy
            merged_changes = self._apply_merge_strategy(
                source_changes,
                target_changes,
                conflicts,
                strategy,
            )

            # Create new version with merged changes
            merged_version = await self.create_version(
                budget_id=source.budget_id,
                name=f"Merge {source.name} into {target.name}",
                changes=merged_changes,
                parent_id=target_version_id,
                author=author,
                metadata={
                    "merge_source": source_version_id,
                    "merge_target": target_version_id,
                    "merge_strategy": strategy,
                },
            )

            return MergeResult(
                success=True,
                merged_version_id=merged_version.id,
                changes_applied=merged_changes,
                metadata={"status": "merged_successfully"},
            )

        finally:
            # Record processing time
            duration = (datetime.utcnow() - start_time).total_seconds()
            METRICS["version_processing_time"].observe(duration)

    async def get_version(self, version_id: str) -> Optional[Version]:
        """Get a version by ID.

        Args:
            version_id: ID of the version

        Returns:
            Version if found
        """
        # Check cache
        if version_id in self.version_cache:
            return self.version_cache[version_id]

        # Get from storage
        if self.storage:
            data = await self.storage.get_version(version_id)
            if data:
                version = Version.parse_obj(data)
                self.version_cache[version_id] = version
                return version

        return None

    async def get_version_graph(self, budget_id: str) -> VersionGraph:
        """Get version graph for a budget.

        Args:
            budget_id: ID of the budget

        Returns:
            Version graph
        """
        # Create directed graph
        G = nx.DiGraph()

        # Get all versions for budget
        versions = await self._get_budget_versions(budget_id)
        branches = await self._get_budget_branches(budget_id)

        # Add nodes (versions)
        for version in versions:
            G.add_node(version.id, data=version.dict(exclude={"changes"}))

        # Add edges (parent relationships)
        for version in versions:
            if version.parent_id:
                G.add_edge(version.parent_id, version.id)

        # Convert to serializable format
        return VersionGraph(
            budget_id=budget_id,
            nodes=[{"id": node, "data": G.nodes[node]["data"]} for node in G.nodes()],
            edges=[
                {"source": source, "target": target} for source, target in G.edges()
            ],
            branches=[branch.dict() for branch in branches],
        )

    async def compare_versions(
        self,
        base_version_id: str,
        target_version_id: str,
    ) -> VersionDiff:
        """Compare two versions.

        Args:
            base_version_id: ID of base version
            target_version_id: ID of target version

        Returns:
            Version difference
        """
        # Get changes since common ancestor
        ancestor_id = await self._find_common_ancestor(
            base_version_id, target_version_id
        )
        base_changes = await self._get_changes_since(base_version_id, ancestor_id)
        target_changes = await self._get_changes_since(target_version_id, ancestor_id)

        # Create summary
        summary = self._create_diff_summary(base_changes, target_changes)

        return VersionDiff(
            base_version_id=base_version_id,
            target_version_id=target_version_id,
            changes=target_changes,
            summary=summary,
        )

    async def _get_next_version_number(self, budget_id: str) -> int:
        """Get next version number for a budget."""
        versions = await self._get_budget_versions(budget_id)
        if not versions:
            return 1
        return max(v.number for v in versions) + 1

    async def _get_budget_versions(self, budget_id: str) -> List[Version]:
        """Get all versions for a budget."""
        if self.storage:
            versions_data = await self.storage.get_budget_versions(budget_id)
            return [Version.parse_obj(data) for data in versions_data]
        return []

    async def _get_budget_branches(self, budget_id: str) -> List[Branch]:
        """Get all branches for a budget."""
        if self.storage:
            branches_data = await self.storage.get_budget_branches(budget_id)
            return [Branch.parse_obj(data) for data in branches_data]
        return []

    async def _find_common_ancestor(
        self, version1_id: str, version2_id: str
    ) -> Optional[str]:
        """Find common ancestor of two versions."""
        v1_ancestors = await self._get_ancestor_ids(version1_id)
        v2_ancestors = await self._get_ancestor_ids(version2_id)
        common = v1_ancestors.intersection(v2_ancestors)
        return max(common, key=lambda x: self.version_cache[x].number)

    async def _get_ancestor_ids(self, version_id: str) -> Set[str]:
        """Get set of ancestor IDs for a version."""
        ancestors = set()
        current = await self.get_version(version_id)
        while current and current.parent_id:
            ancestors.add(current.id)
            current = await self.get_version(current.parent_id)
        if current:
            ancestors.add(current.id)
        return ancestors

    async def _get_changes_since(
        self, version_id: str, ancestor_id: str
    ) -> List[Change]:
        """Get all changes from ancestor to version."""
        changes = []
        current = await self.get_version(version_id)
        while current and current.id != ancestor_id:
            changes.extend(current.changes)
            if not current.parent_id:
                break
            current = await self.get_version(current.parent_id)
        return changes

    def _find_conflicts(
        self,
        source_changes: List[Change],
        target_changes: List[Change],
    ) -> List[Dict[str, Any]]:
        """Find conflicts between two sets of changes."""
        conflicts = []
        source_fields = {
            (change.type, change.field): change for change in source_changes
        }
        target_fields = {
            (change.type, change.field): change for change in target_changes
        }

        # Find overlapping fields
        for key in source_fields.keys() & target_fields.keys():
            source_change = source_fields[key]
            target_change = target_fields[key]
            if source_change.new_value != target_change.new_value:
                conflicts.append(
                    {
                        "field": key[1],
                        "type": key[0],
                        "source_change": source_change.dict(),
                        "target_change": target_change.dict(),
                    }
                )

        return conflicts

    def _apply_merge_strategy(
        self,
        source_changes: List[Change],
        target_changes: List[Change],
        conflicts: List[Dict[str, Any]],
        strategy: MergeStrategy,
    ) -> List[Change]:
        """Apply merge strategy to resolve conflicts."""
        if not conflicts:
            return source_changes + target_changes

        # Create map of conflicting fields
        conflict_fields = {(c["type"], c["field"]): c for c in conflicts}

        # Apply strategy
        merged = []
        used_fields = set()

        for change in source_changes + target_changes:
            key = (change.type, change.field)
            if key in conflict_fields:
                if key not in used_fields:
                    if strategy == MergeStrategy.OURS:
                        merged.append(change)
                    elif strategy == MergeStrategy.THEIRS:
                        conflict = conflict_fields[key]
                        merged.append(Change.parse_obj(conflict["target_change"]))
                    used_fields.add(key)
            else:
                merged.append(change)

        return merged

    def _create_diff_summary(
        self,
        base_changes: List[Change],
        target_changes: List[Change],
    ) -> Dict[str, Any]:
        """Create summary of differences between changes."""
        summary = {
            "total_changes": len(target_changes),
            "changes_by_type": {},
            "modified_fields": set(),
        }

        for change in target_changes:
            # Count by type
            if change.type not in summary["changes_by_type"]:
                summary["changes_by_type"][change.type] = 0
            summary["changes_by_type"][change.type] += 1

            # Track modified fields
            summary["modified_fields"].add(change.field)

        # Convert set to list for JSON serialization
        summary["modified_fields"] = list(summary["modified_fields"])

        return summary
