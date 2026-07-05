"""Tests for Atlas CycloneDX BOM generator."""

from __future__ import annotations

import json
from pathlib import Path

from atlas.generators.cyclonedx import generate_bom
from atlas.graph.mapper import build_topology
from atlas.models import Component, ComponentSource, ComponentType, Framework
from atlas.risk.classifier import classify_system


def _make_component(comp_type: ComponentType, name: str) -> Component:
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
        model_name="gpt-4" if comp_type == ComponentType.MODEL else None,
        provider="openai" if comp_type == ComponentType.MODEL else None,
    )


class TestBomGenerator:
    def test_generates_valid_json(self) -> None:
        components = [
            _make_component(ComponentType.MODEL, "llm"),
            _make_component(ComponentType.AGENT, "agent"),
        ]
        topology = build_topology(components)
        output = generate_bom(components, topology, output_format="json")

        bom = json.loads(output)
        assert bom["bomFormat"] == "CycloneDX"
        assert bom["specVersion"] == "1.6"
        assert bom["version"] == 1
        assert "serialNumber" in bom
        assert len(bom["components"]) == 2

    def test_generates_xml(self) -> None:
        components = [_make_component(ComponentType.MODEL, "llm")]
        topology = build_topology(components)
        output = generate_bom(components, topology, output_format="xml")

        assert "cyclonedx.org/schema/bom/1.6" in output
        assert "<name>llm</name>" in output

    def test_includes_risk_metadata(self) -> None:
        components = [
            _make_component(ComponentType.AGENT, "agent"),
            _make_component(ComponentType.TOOL, "tool"),
        ]
        topology = build_topology(components)
        risk = classify_system(components, topology)
        output = generate_bom(components, topology, risk, output_format="json")

        bom = json.loads(output)
        props = bom["metadata"]["properties"]
        prop_names = [p["name"] for p in props]
        assert "atlas:risk:tier" in prop_names
        assert "atlas:risk:score" in prop_names

    def test_includes_dependencies(self) -> None:
        components = [
            _make_component(ComponentType.AGENT, "agent"),
            _make_component(ComponentType.MODEL, "llm"),
        ]
        topology = build_topology(components)
        output = generate_bom(components, topology, output_format="json")

        bom = json.loads(output)
        assert len(bom["dependencies"]) > 0

    def test_model_has_model_card(self) -> None:
        components = [_make_component(ComponentType.MODEL, "llm")]
        topology = build_topology(components)
        output = generate_bom(components, topology, output_format="json")

        bom = json.loads(output)
        model_component = bom["components"][0]
        assert "modelCard" in model_component
