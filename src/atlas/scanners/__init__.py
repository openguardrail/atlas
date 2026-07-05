"""AI system scanners for discovering components in project codebases."""

from __future__ import annotations

from pathlib import Path

from atlas.models import Component, Framework, ScanResult
from atlas.scanners.autogen_scanner import AutoGenScanner
from atlas.scanners.crewai_scanner import CrewAIScanner
from atlas.scanners.generic_scanner import GenericScanner
from atlas.scanners.langchain_scanner import LangChainScanner

SCANNERS = [
    LangChainScanner(),
    CrewAIScanner(),
    AutoGenScanner(),
    GenericScanner(),
]


def scan_project(path: Path) -> ScanResult:
    """Scan a project directory for AI system components.

    Runs all framework-specific scanners and merges results.

    Args:
        path: Root directory of the project to scan.

    Returns:
        ScanResult with all discovered components and relationships.
    """
    all_components: list[Component] = []
    all_frameworks: list[Framework] = []

    python_files = list(path.rglob("*.py"))

    for scanner in SCANNERS:
        result = scanner.scan(python_files, path)
        if result.components:
            all_components.extend(result.components)
            all_frameworks.extend(result.frameworks_detected)

    # Deduplicate frameworks
    unique_frameworks = list(set(all_frameworks))

    # Collect all relationships
    all_relationships = []
    for component in all_components:
        all_relationships.extend(component.relationships)

    return ScanResult(
        components=all_components,
        relationships=all_relationships,
        frameworks_detected=unique_frameworks,
        scan_path=path,
    )
