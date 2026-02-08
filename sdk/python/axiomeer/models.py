"""
Data models for Axiomeer SDK
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AppListing:
    """Represents an application/tool in the marketplace"""
    app_id: str
    name: str
    description: str
    provider: str
    capabilities: List[str] = field(default_factory=list)
    trust_card: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    uptime: Optional[float] = None

    def __str__(self):
        return f"{self.name} (by {self.provider})"


@dataclass
class ShopResult:
    """Result from shopping for a tool"""
    selected_app: AppListing
    reasoning: str
    confidence: float
    alternatives: List[AppListing] = field(default_factory=list)

    def execute(self, marketplace, task: str = "", **params):
        """
        Execute the selected tool with given parameters.

        Args:
            marketplace: AgentMarketplace instance
            task: Task description (optional)
            **params: Tool-specific parameters

        Returns:
            ExecutionResult
        """
        if not task:
            task = f"Execute {self.selected_app.name}"

        return marketplace.execute(
            app_id=self.selected_app.app_id,
            params=params,
            task=task
        )

    def __str__(self):
        return (
            f"ShopResult(\n"
            f"  Selected: {self.selected_app}\n"
            f"  Reasoning: {self.reasoning}\n"
            f"  Confidence: {self.confidence:.2%}\n"
            f"  Alternatives: {len(self.alternatives)}\n"
            f")"
        )


@dataclass
class ExecutionResult:
    """Result from executing a tool"""
    success: bool
    result: Any
    app_id: str
    execution_time_ms: Optional[float] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None

    def __str__(self):
        if self.success:
            return f"ExecutionResult(success=True, result={self.result})"
        else:
            return f"ExecutionResult(success=False, error={self.error})"

    @property
    def data(self):
        """Alias for result for convenience"""
        return self.result
