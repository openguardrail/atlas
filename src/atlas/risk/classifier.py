"""Risk classification for AI systems.

Supports risk categorization aligned with:
- EU AI Act (Unacceptable, High, Limited, Minimal)
- NIST AI Risk Management Framework (AI RMF)
- ISO/IEC 42001 AI Management System
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from atlas.models import Component, ComponentType

if TYPE_CHECKING:
    from atlas.graph.mapper import Topology


class RiskTier(Enum):
    """Risk classification tiers."""

    UNACCEPTABLE = "unacceptable"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"


@dataclass
class RiskFactor:
    """A specific risk factor identified in the system."""

    name: str
    description: str
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "autonomy", "data", "transparency", "security", "fairness"


@dataclass
class RiskAssessment:
    """Complete risk assessment for an AI system."""

    tier: RiskTier
    score: float  # 0.0 - 1.0
    factors: list[RiskFactor] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def print_report(self, console: Console) -> None:
        """Print a formatted risk report."""
        tier_colors = {
            RiskTier.UNACCEPTABLE: "red",
            RiskTier.HIGH: "bright_red",
            RiskTier.LIMITED: "yellow",
            RiskTier.MINIMAL: "green",
        }

        color = tier_colors[self.tier]
        console.print(f"\n[bold]Risk Classification:[/] [{color}]{self.tier.value.upper()}[/]")
        console.print(f"[bold]Risk Score:[/] {self.score:.2f}/1.00\n")

        if self.factors:
            table = Table(title="Risk Factors")
            table.add_column("Factor", style="bold")
            table.add_column("Category")
            table.add_column("Severity")
            table.add_column("Description")

            for factor in self.factors:
                severity_color = {
                    "critical": "red",
                    "high": "bright_red",
                    "medium": "yellow",
                    "low": "green",
                }.get(factor.severity, "white")

                table.add_row(
                    factor.name,
                    factor.category,
                    f"[{severity_color}]{factor.severity}[/]",
                    factor.description,
                )

            console.print(table)

        if self.recommendations:
            console.print("\n[bold]Recommendations:[/]")
            for rec in self.recommendations:
                console.print(f"  • {rec}")
        console.print()


def classify_system(
    components: list[Component] | None = None,
    topology: Topology | None = None,
) -> RiskAssessment:
    """Classify an AI system's risk tier.

    Evaluates system characteristics against risk categories from
    EU AI Act, NIST AI RMF, and ISO/IEC 42001.

    Args:
        components: List of discovered components.
        topology: System dependency graph.

    Returns:
        RiskAssessment with tier, score, factors, and recommendations.
    """
    if components is None:
        components = []

    factors: list[RiskFactor] = []
    recommendations: list[str] = []

    # Analyze system characteristics
    has_agents = any(c.component_type == ComponentType.AGENT for c in components)
    has_orchestrator = any(c.component_type == ComponentType.ORCHESTRATOR for c in components)
    has_memory = any(c.component_type == ComponentType.MEMORY for c in components)
    has_tools = any(c.component_type == ComponentType.TOOL for c in components)
    has_guardrails = any(c.component_type == ComponentType.GUARDRAIL for c in components)
    model_count = sum(1 for c in components if c.component_type == ComponentType.MODEL)
    agent_count = sum(1 for c in components if c.component_type == ComponentType.AGENT)

    # Autonomy risk - agents that can act independently
    if has_agents and has_tools:
        factors.append(RiskFactor(
            name="Autonomous tool use",
            description="Agents have access to tools and can execute actions",
            severity="high",
            category="autonomy",
        ))
        if not has_guardrails:
            factors.append(RiskFactor(
                name="No guardrails detected",
                description="No validation or safety constraints on agent actions",
                severity="critical",
                category="security",
            ))
            recommendations.append(
                "Add guardrails to validate agent actions before execution"
            )

    # Multi-agent coordination risk
    if agent_count > 1 and has_orchestrator:
        factors.append(RiskFactor(
            name="Multi-agent orchestration",
            description=f"{agent_count} agents coordinated by an orchestrator",
            severity="high",
            category="autonomy",
        ))
        recommendations.append(
            "Implement agent communication logging and decision audit trails"
        )

    # Data persistence and memory risk
    if has_memory:
        factors.append(RiskFactor(
            name="Persistent memory",
            description="System retains information across interactions",
            severity="medium",
            category="data",
        ))
        recommendations.append(
            "Implement data retention policies and memory audit capabilities"
        )

    # Model complexity risk
    if model_count > 1:
        factors.append(RiskFactor(
            name="Multi-model architecture",
            description=f"{model_count} models in the system",
            severity="medium",
            category="transparency",
        ))
        recommendations.append(
            "Document model selection logic and fallback behavior"
        )

    # Transparency risk - no clear single model
    if has_agents and not has_guardrails:
        factors.append(RiskFactor(
            name="Limited transparency",
            description="Autonomous system without visible safety constraints",
            severity="high",
            category="transparency",
        ))

    # Graph complexity (if topology available)
    if topology and topology.graph.number_of_edges() > 10:
        factors.append(RiskFactor(
            name="Complex dependency graph",
            description=f"System has {topology.graph.number_of_edges()} component relationships",
            severity="medium",
            category="transparency",
        ))

    # Calculate score and tier
    score = _calculate_risk_score(factors)
    tier = _score_to_tier(score)

    return RiskAssessment(
        tier=tier,
        score=score,
        factors=factors,
        recommendations=recommendations,
    )


def _calculate_risk_score(factors: list[RiskFactor]) -> float:
    """Calculate a 0.0-1.0 risk score from factors."""
    if not factors:
        return 0.0

    severity_weights = {
        "critical": 0.4,
        "high": 0.25,
        "medium": 0.15,
        "low": 0.05,
    }

    total = sum(severity_weights.get(f.severity, 0.1) for f in factors)
    return min(total, 1.0)


def _score_to_tier(score: float) -> RiskTier:
    """Map a risk score to a risk tier."""
    if score >= 0.8:
        return RiskTier.UNACCEPTABLE
    elif score >= 0.5:
        return RiskTier.HIGH
    elif score >= 0.25:
        return RiskTier.LIMITED
    else:
        return RiskTier.MINIMAL
