"""Base scanner interface."""

from __future__ import annotations

import ast
import re
from abc import ABC, abstractmethod
from pathlib import Path

from atlas.models import Component, Framework, ScanResult


class BaseScanner(ABC):
    """Base class for all AI framework scanners."""

    @property
    @abstractmethod
    def framework(self) -> Framework:
        """The framework this scanner detects."""

    @property
    @abstractmethod
    def import_patterns(self) -> list[str]:
        """Import patterns that indicate this framework is used."""

    def scan(self, files: list[Path], root: Path) -> ScanResult:
        """Scan files for AI components from this framework.

        Args:
            files: Python files to scan.
            root: Project root path.

        Returns:
            ScanResult with discovered components.
        """
        relevant_files = self._filter_relevant_files(files)

        if not relevant_files:
            return ScanResult(
                components=[],
                relationships=[],
                frameworks_detected=[],
                scan_path=root,
            )

        components: list[Component] = []
        for file in relevant_files:
            try:
                source = file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(file))
                found = self._extract_components(tree, source, file, root)
                components.extend(found)
            except (SyntaxError, UnicodeDecodeError):
                continue

        return ScanResult(
            components=components,
            relationships=[],
            frameworks_detected=[self.framework] if components else [],
            scan_path=root,
        )

    def _filter_relevant_files(self, files: list[Path]) -> list[Path]:
        """Filter files that import this framework."""
        relevant = []
        for file in files:
            try:
                content = file.read_text(encoding="utf-8")
                if any(re.search(pattern, content) for pattern in self.import_patterns):
                    relevant.append(file)
            except (UnicodeDecodeError, OSError):
                continue
        return relevant

    @abstractmethod
    def _extract_components(
        self, tree: ast.Module, source: str, file: Path, root: Path
    ) -> list[Component]:
        """Extract AI components from an AST.

        Args:
            tree: Parsed AST of the file.
            source: Raw source code.
            file: Path to the file.
            root: Project root.

        Returns:
            List of discovered components.
        """
