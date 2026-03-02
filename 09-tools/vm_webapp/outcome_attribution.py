"""Outcome attribution engine for v36.

Attributes outcomes (activation, recovery, resume) to touchpoints
using configurable attribution models (linear, first-touch, last-touch).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
import uuid


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class OutcomeType(str, Enum):
    """Types of outcomes that can be attributed."""
    ACTIVATION = "activation"
    RECOVERY = "recovery"
    RESUME = "resume"
    FIRST_RUN = "first_run"
    FEATURE_ADOPTION = "feature_adoption"


class TouchpointType(str, Enum):
    """Types of touchpoints that can contribute to outcomes."""
    ONBOARDING_STEP = "onboarding_step"
    RECOVERY_ACTION = "recovery_action"
    CONTINUITY_RESUME = "continuity_resume"
    NUDGE = "nudge"
    SUPPORT_INTERACTION = "support_interaction"
    SELF_SERVICE = "self_service"


@dataclass
class AttributionWindow:
    """Time window for attribution analysis."""
    days: int = 30
    
    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp falls within window."""
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.days)
        return timestamp >= cutoff


@dataclass
class ContributionWeight:
    """Weight of a touchpoint's contribution to an outcome."""
    value: float
    confidence: float = 1.0
    
    def __post_init__(self):
        """Validate weight range."""
        if not 0 <= self.value <= 1:
            raise ValueError(f"Weight value must be between 0 and 1, got {self.value}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
    
    def adjust(self, factor: float) -> ContributionWeight:
        """Return new weight adjusted by factor."""
        return ContributionWeight(
            value=max(0.0, min(1.0, self.value * factor)),
            confidence=self.confidence * factor
        )


@dataclass
class AttributionNode:
    """A touchpoint node in the attribution graph."""
    node_id: str
    touchpoint_type: TouchpointType
    touchpoint_id: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert node to dictionary."""
        return {
            "node_id": self.node_id,
            "touchpoint_type": self.touchpoint_type.value,
            "touchpoint_id": self.touchpoint_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class AttributionGraph:
    """Graph of touchpoints leading to an outcome."""
    graph_id: str
    user_id: str
    brand_id: str
    outcome_type: OutcomeType
    nodes: List[AttributionNode] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    outcome_timestamp: Optional[str] = None
    
    def add_node(self, node: AttributionNode) -> None:
        """Add a touchpoint node to the graph."""
        self.nodes.append(node)
        # Sort by timestamp
        self.nodes.sort(key=lambda n: n.timestamp)
    
    def calculate_contributions(
        self, 
        method: str = "linear"
    ) -> List[ContributionWeight]:
        """Calculate contribution weights using specified method."""
        if not self.nodes:
            return []
        
        n = len(self.nodes)
        
        if method == "linear":
            # Equal distribution
            weight = 1.0 / n
            return [ContributionWeight(value=weight) for _ in range(n)]
        
        elif method == "first_touch":
            # All credit to first touchpoint
            weights = [ContributionWeight(value=0.0) for _ in range(n)]
            weights[0] = ContributionWeight(value=1.0)
            return weights
        
        elif method == "last_touch":
            # All credit to last touchpoint
            weights = [ContributionWeight(value=0.0) for _ in range(n)]
            weights[-1] = ContributionWeight(value=1.0)
            return weights
        
        elif method == "time_decay":
            # Exponential decay from last touch
            weights = []
            total = 0.0
            for i in range(n):
                w = 2 ** (i / (n - 1) if n > 1 else 1)
                weights.append(w)
                total += w
            return [ContributionWeight(value=w/total) for w in weights]
        
        else:
            # Default to linear
            weight = 1.0 / n
            return [ContributionWeight(value=weight) for _ in range(n)]
    
    def to_dict(self) -> dict:
        """Convert graph to dictionary."""
        return {
            "graph_id": self.graph_id,
            "user_id": self.user_id,
            "brand_id": self.brand_id,
            "outcome_type": self.outcome_type.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "created_at": self.created_at,
            "outcome_timestamp": self.outcome_timestamp,
        }


# Fix forward reference
from datetime import timedelta


class OutcomeAttributionEngine:
    """Engine for attributing outcomes to touchpoints."""
    
    def __init__(self, window: Optional[AttributionWindow] = None):
        """Initialize engine with attribution window."""
        self.window = window or AttributionWindow()
        self.touchpoints: List[Dict[str, Any]] = []
        self.graphs: Dict[str, AttributionGraph] = {}
    
    def create_graph(
        self,
        user_id: str,
        brand_id: str,
        outcome_type: OutcomeType,
        graph_id: Optional[str] = None,
    ) -> AttributionGraph:
        """Create a new attribution graph."""
        graph = AttributionGraph(
            graph_id=graph_id or str(uuid.uuid4()),
            user_id=user_id,
            brand_id=brand_id,
            outcome_type=outcome_type,
        )
        self.graphs[graph.graph_id] = graph
        return graph
    
    def record_touchpoint(
        self,
        user_id: str,
        brand_id: str,
        touchpoint_type: TouchpointType,
        touchpoint_id: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttributionNode:
        """Record a touchpoint for later attribution."""
        node = AttributionNode(
            node_id=str(uuid.uuid4()),
            touchpoint_type=touchpoint_type,
            touchpoint_id=touchpoint_id,
            timestamp=timestamp or _now_iso(),
            metadata=metadata or {},
        )
        self.touchpoints.append({
            "user_id": user_id,
            "brand_id": brand_id,
            "node": node,
        })
        return node
    
    def attribute_outcome(
        self,
        user_id: str,
        brand_id: str,
        outcome_type: OutcomeType,
        method: str = "linear",
        outcome_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Attribute an outcome to touchpoints."""
        # Create graph
        graph = self.create_graph(
            user_id=user_id,
            brand_id=brand_id,
            outcome_type=outcome_type,
        )
        graph.outcome_timestamp = outcome_timestamp or _now_iso()
        
        # Filter touchpoints for this user/brand within window
        relevant = [
            t for t in self.touchpoints
            if t["user_id"] == user_id 
            and t["brand_id"] == brand_id
            and self.window.contains(t["node"].timestamp)
        ]
        
        # Add nodes to graph
        for t in relevant:
            graph.add_node(t["node"])
        
        # Calculate contributions
        weights = graph.calculate_contributions(method)
        
        # Build result
        contributions = []
        for i, node in enumerate(graph.nodes):
            contributions.append({
                "node_id": node.node_id,
                "touchpoint_type": node.touchpoint_type.value,
                "touchpoint_id": node.touchpoint_id,
                "timestamp": node.timestamp,
                "weight": weights[i].value,
                "confidence": weights[i].confidence,
            })
        
        return {
            "graph_id": graph.graph_id,
            "user_id": user_id,
            "brand_id": brand_id,
            "outcome_type": outcome_type.value,
            "method": method,
            "contributions": contributions,
            "total_touchpoints": len(contributions),
        }
    
    def get_attribution_summary(self, brand_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of attribution data."""
        graphs = list(self.graphs.values())
        if brand_id:
            graphs = [g for g in graphs if g.brand_id == brand_id]
        
        total_outcomes = len(graphs)
        total_touchpoints = sum(len(g.nodes) for g in graphs)
        
        by_outcome = {}
        for outcome_type in OutcomeType:
            count = len([g for g in graphs if g.outcome_type == outcome_type])
            if count > 0:
                by_outcome[outcome_type.value] = count
        
        return {
            "total_outcomes": total_outcomes,
            "total_touchpoints": total_touchpoints,
            "by_outcome_type": by_outcome,
            "window_days": self.window.days,
        }
