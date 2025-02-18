"""Base agent functionality."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AgentMetric(BaseModel):
    """Simple metric tracking."""

    name: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentAction(BaseModel):
    """Basic action tracking."""

    action_type: str
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    success: bool = False
    error: Optional[str] = None
    metrics: List[AgentMetric] = Field(default_factory=list)


class AgentCore:
    """Simple but extensible agent core."""

    def __init__(self):
        self.actions: List[AgentAction] = []
        self._current_action: Optional[AgentAction] = None

    async def start_action(self, action_type: str) -> None:
        """Start tracking a new action."""
        self._current_action = AgentAction(action_type=action_type)

    async def end_action(self, success: bool, error: str = None) -> None:
        """End current action and store metrics."""
        if self._current_action:
            self._current_action.end_time = datetime.now()
            self._current_action.success = success
            self._current_action.error = error
            self.actions.append(self._current_action)
            self._current_action = None

    async def add_metric(self, name: str, value: float) -> None:
        """Add a metric to current action."""
        if self._current_action:
            metric = AgentMetric(name=name, value=value)
            self._current_action.metrics.append(metric)

    def get_recent_metrics(self, limit: int = 10) -> Dict[str, List[float]]:
        """Get recent metrics grouped by name."""
        metrics: Dict[str, List[float]] = {}

        # Get metrics from recent actions
        for action in self.actions[-limit:]:
            for metric in action.metrics:
                if metric.name not in metrics:
                    metrics[metric.name] = []
                metrics[metric.name].append(metric.value)

        return metrics

    def get_success_rate(self, action_type: str = None) -> float:
        """Calculate success rate for all or specific action type."""
        relevant_actions = [
            a for a in self.actions if not action_type or a.action_type == action_type
        ]

        if not relevant_actions:
            return 0.0

        successful = sum(1 for a in relevant_actions if a.success)
        return successful / len(relevant_actions)
