"""Generic scanner for common AI patterns not tied to a specific framework."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from atlas.models import Component, ComponentSource, ComponentType, Framework
from atlas.scanners.base import BaseScanner

# API client patterns that indicate AI model usage
API_PATTERNS: dict[str, tuple[ComponentType, str]] = {
    "openai.OpenAI": (ComponentType.MODEL, "openai"),
    "openai.AsyncOpenAI": (ComponentType.MODEL, "openai"),
    "anthropic.Anthropic": (ComponentType.MODEL, "anthropic"),
    "anthropic.AsyncAnthropic": (ComponentType.MODEL, "anthropic"),
    "google.generativeai": (ComponentType.MODEL, "google"),
    "cohere.Client": (ComponentType.MODEL, "cohere"),
    "replicate.run": (ComponentType.MODEL, "replicate"),
}

# Regex patterns for detecting AI-related imports
GENERIC_IMPORT_PATTERNS = [
    r"from\s+openai",
    r"import\s+openai",
    r"from\s+anthropic",
    r"import\s+anthropic",
    r"from\s+google\.generativeai",
    r"import\s+google\.generativeai",
    r"from\s+transformers",
    r"import\s+transformers",
    r"from\s+sentence_transformers",
    r"import\s+cohere",
    r"from\s+pinecone",
    r"from\s+chromadb",
    r"from\s+qdrant_client",
    r"from\s+weaviate",
]


class GenericScanner(BaseScanner):
    """Scanner for generic AI patterns (direct API clients, transformers, etc.)."""

    @property
    def framework(self) -> Framework:
        return Framework.CUSTOM

    @property
    def import_patterns(self) -> list[str]:
        return GENERIC_IMPORT_PATTERNS

    def _extract_components(
        self, tree: ast.Module, source: str, file: Path, root: Path
    ) -> list[Component]:
        """Extract generic AI components from AST."""
        components: list[Component] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check API client patterns
                full_name = self._get_full_call_name(node)
                if full_name:
                    component = self._match_api_pattern(full_name, node, file, root)
                    if component:
                        components.append(component)
                        continue

                    # Check transformers model loading patterns
                    component = self._detect_transformers_model(node, file, root)
                    if component:
                        components.append(component)

        # Detect vector store clients from imports
        import_components = self._detect_vectorstore_imports(tree, source, file, root)
        components.extend(import_components)

        return components

    def _get_full_call_name(self, node: ast.Call) -> str | None:
        """Get full dotted name from a Call node."""
        if isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        if isinstance(node.func, ast.Name):
            return node.func.id
        return None

    def _match_api_pattern(
        self, name: str, node: ast.Call, file: Path, root: Path
    ) -> Component | None:
        """Check if a call matches known API client patterns."""
        for pattern, (comp_type, provider) in API_PATTERNS.items():
            if pattern in name or name.endswith(pattern.split(".")[-1]):
                return Component(
                    id=self._generate_id(name, file, node.lineno),
                    name=name.split(".")[-1],
                    component_type=comp_type,
                    source=ComponentSource(
                        file=file.relative_to(root),
                        line=node.lineno,
                        framework=Framework.CUSTOM,
                    ),
                    provider=provider,
                    properties=self._extract_properties(node),
                )
        return None

    def _detect_transformers_model(
        self, node: ast.Call, file: Path, root: Path
    ) -> Component | None:
        """Detect HuggingFace transformers model loading."""
        name = self._get_full_call_name(node)
        if not name:
            return None

        model_load_patterns = [
            "from_pretrained",
            "AutoModel.from_pretrained",
            "AutoModelForCausalLM.from_pretrained",
            "AutoModelForSequenceClassification.from_pretrained",
        ]

        if any(p in name for p in model_load_patterns):
            model_name = None
            if node.args and isinstance(node.args[0], ast.Constant):
                model_name = str(node.args[0].value)

            return Component(
                id=self._generate_id(name, file, node.lineno),
                name=model_name or name,
                component_type=ComponentType.MODEL,
                source=ComponentSource(
                    file=file.relative_to(root),
                    line=node.lineno,
                    framework=Framework.CUSTOM,
                ),
                model_name=model_name,
                provider="huggingface",
            )
        return None

    def _detect_vectorstore_imports(
        self, tree: ast.Module, source: str, file: Path, root: Path
    ) -> list[Component]:
        """Detect vector store usage from imports."""
        components: list[Component] = []
        vectorstore_imports = {
            "chromadb": "chroma",
            "pinecone": "pinecone",
            "qdrant_client": "qdrant",
            "weaviate": "weaviate",
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    module = node.names[0].name if node.names else ""

                for pkg, store_name in vectorstore_imports.items():
                    if pkg in module:
                        components.append(
                            Component(
                                id=self._generate_id(store_name, file, node.lineno),
                                name=store_name,
                                component_type=ComponentType.VECTOR_STORE,
                                source=ComponentSource(
                                    file=file.relative_to(root),
                                    line=node.lineno,
                                    framework=Framework.CUSTOM,
                                ),
                                provider=store_name,
                            )
                        )
        return components

    def _extract_properties(self, node: ast.Call) -> dict[str, str]:
        """Extract non-sensitive properties from constructor kwargs."""
        safe_keys = {"model", "temperature", "max_tokens", "timeout", "base_url"}
        props: dict[str, str] = {}
        for keyword in node.keywords:
            if keyword.arg and keyword.arg in safe_keys and isinstance(keyword.value, ast.Constant):
                props[keyword.arg] = str(keyword.value.value)
        return props

    def _generate_id(self, name: str, file: Path, line: int) -> str:
        """Generate a stable component ID."""
        raw = f"{file}:{line}:{name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
