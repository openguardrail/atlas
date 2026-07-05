"""Tests for Atlas risk classifier."""

from __future__ import annotations

from pathlib import Path

from atlas.models import Component, ComponentSource, ComponentType, Framework
from atlas.risk.classifier import RiskTier, classify_system


def _make_component(comp_type: ComponentType, name: str = "test") -> Component:
    """Create a test component."""
    return Component(
        id=f"test-{name}",
        name=name,
        component_type=comp_type,
        source=ComponentSource(
            file=Path("test.py"),
            line=1,
            framework=Framework.LANGCHAIN,
        ),
    )


class TestRiskClassifier:
    def test_minimal_risk_single_model(self) -> None:
        components = [_make_component(ComponentType.MODEL, "gpt-4")]
        assessment = classify_system(components)
        assert assessment.tier == RiskTier.MINIMAL
        assert assessment.score < 0.25

    def test_high_risk_agents_with_tools_no_guardrails(self) -> None:
        components = [
            _make_component(ComponentType.AGENT, "researcher"),
            _make_component(ComponentType.AGENT, "writer"),
            _make_component(ComponentType.TOOL, "web_search"),
            _make_component(ComponentType.ORCHESTRATOR, "crew"),
            _make_component(ComponentType.MODEL, "gpt-4"),
        ]
        assessment = classify_system(components)
        assert assessment.tier in (RiskTier.HIGH, RiskTier.UNACCEPTABLE)
        assert assessment.score >= 0.5

    def test_guardrails_reduce_risk(self) -> None:
        # Without guardrails
        components_no_guard = [
            _make_component(ComponentType.AGENT, "agent"),
            _make_component(ComponentType.TOOL, "tool"),
        ]
        assessment_no_guard = classify_system(components_no_guard)

        # With guardrails
        components_with_guard = [
            _make_component(ComponentType.AGENT, "agent"),
            _make_component(ComponentType.TOOL, "tool"),
            _make_component(ComponentType.GUARDRAIL, "validator"),
        ]
        assessment_with_guard = classify_system(components_with_guard)

        assert assessment_with_guard.score < assessment_no_guard.score

    def test_empty_system(self) -> None:
        assessment = classify_system([])
        assert assessment.tier == RiskTier.MINIMAL
        assert assessment.score == 0.0

    def test_recommendations_for_no_guardrails(self) -> None:
        components = [
            _make_component(ComponentType.AGENT, "agent"),
            _make_component(ComponentType.TOOL, "tool"),
        ]
        assessment = classify_system(components)
        assert len(assessment.recommendations) > 0
        assert any("guardrail" in r.lower() for r in assessment.recommendations)
