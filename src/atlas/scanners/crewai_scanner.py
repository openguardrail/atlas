"""CrewAI framework scanner."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from atlas.models import Component, ComponentSource, ComponentType, Framework
from atlas.scanners.base import BaseScanner

CREWAI_COMPONENT_MAP: dict[str, ComponentType] = {
    "Agent": ComponentType.AGENT,
    "Task": ComponentType.TOOL,
    "Crew": ComponentType.ORCHESTRATOR,
    "Process": ComponentType.ROUTER,
}


class CrewAIScanner(BaseScanner):
    """Scanner for CrewAI-based multi-agent systems."""

    @property
    def framework(self) -> Framework:
        return Framework.CREWAI

    @property
    def import_patterns(self) -> list[str]:
        return [
            r"from\s+crewai",
            r"import\s+crewai",
        ]

    def _extract_components(
        self, tree: ast.Module, source: str, file: Path, root: Path
    ) -> list[Component]:
        """Extract CrewAI components from AST."""
        components: list[Component] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = self._get_call_name(node)
                if name and name in CREWAI_COMPONENT_MAP:
                    component = self._create_component(name, node, file, root)
                    components.append(component)

        return components

    def _get_call_name(self, node: ast.Call) -> str | None:
        """Get the function/class name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _create_component(
        self, name: str, node: ast.Call, file: Path, root: Path
    ) -> Component:
        """Create a Component from a CrewAI Call node."""
        component_type = CREWAI_COMPONENT_MAP[name]
        component_id = self._generate_id(name, file, node.lineno)

        # Extract agent role/goal if available
        properties = self._extract_properties(node)
        description = properties.get("role") or properties.get("goal")

        return Component(
            id=component_id,
            name=name,
            component_type=component_type,
            source=ComponentSource(
                file=file.relative_to(root),
                line=node.lineno,
                framework=Framework.CREWAI,
            ),
            description=description,
            properties=properties,
        )

    def _extract_properties(self, node: ast.Call) -> dict[str, str]:
        """Extract CrewAI-specific properties."""
        props: dict[str, str] = {}
        for keyword in node.keywords:
            if keyword.arg in ("role", "goal", "backstory", "verbose", "process"):
                if isinstance(keyword.value, ast.Constant):
                    props[keyword.arg] = str(keyword.value.value)
        return props

    def _generate_id(self, name: str, file: Path, line: int) -> str:
        """Generate a stable component ID."""
        raw = f"{file}:{line}:{name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
