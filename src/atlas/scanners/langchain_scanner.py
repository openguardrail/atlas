"""LangChain framework scanner."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from atlas.models import Component, ComponentSource, ComponentType, Framework
from atlas.scanners.base import BaseScanner

# Mapping of LangChain class names to component types
LANGCHAIN_COMPONENT_MAP: dict[str, ComponentType] = {
    # Models
    "ChatOpenAI": ComponentType.MODEL,
    "OpenAI": ComponentType.MODEL,
    "ChatAnthropic": ComponentType.MODEL,
    "ChatGoogleGenerativeAI": ComponentType.MODEL,
    "HuggingFacePipeline": ComponentType.MODEL,
    "Ollama": ComponentType.MODEL,
    "ChatOllama": ComponentType.MODEL,
    # Agents
    "AgentExecutor": ComponentType.AGENT,
    "create_react_agent": ComponentType.AGENT,
    "create_openai_functions_agent": ComponentType.AGENT,
    "create_tool_calling_agent": ComponentType.AGENT,
    # Vector stores
    "Chroma": ComponentType.VECTOR_STORE,
    "FAISS": ComponentType.VECTOR_STORE,
    "Pinecone": ComponentType.VECTOR_STORE,
    "Weaviate": ComponentType.VECTOR_STORE,
    "Qdrant": ComponentType.VECTOR_STORE,
    "Milvus": ComponentType.VECTOR_STORE,
    # Retrievers
    "VectorStoreRetriever": ComponentType.RETRIEVER,
    "MultiQueryRetriever": ComponentType.RETRIEVER,
    "ContextualCompressionRetriever": ComponentType.RETRIEVER,
    # Chains
    "LLMChain": ComponentType.CHAIN,
    "RetrievalQA": ComponentType.CHAIN,
    "ConversationalRetrievalChain": ComponentType.CHAIN,
    "SequentialChain": ComponentType.ORCHESTRATOR,
    # Memory
    "ConversationBufferMemory": ComponentType.MEMORY,
    "ConversationSummaryMemory": ComponentType.MEMORY,
    "VectorStoreRetrieverMemory": ComponentType.MEMORY,
    # Tools
    "Tool": ComponentType.TOOL,
    "StructuredTool": ComponentType.TOOL,
    # Prompt templates
    "ChatPromptTemplate": ComponentType.PROMPT_TEMPLATE,
    "PromptTemplate": ComponentType.PROMPT_TEMPLATE,
}

# Provider detection from model class names
MODEL_PROVIDERS: dict[str, str] = {
    "ChatOpenAI": "openai",
    "OpenAI": "openai",
    "ChatAnthropic": "anthropic",
    "ChatGoogleGenerativeAI": "google",
    "HuggingFacePipeline": "huggingface",
    "Ollama": "ollama",
    "ChatOllama": "ollama",
}


class LangChainScanner(BaseScanner):
    """Scanner for LangChain-based AI systems."""

    @property
    def framework(self) -> Framework:
        return Framework.LANGCHAIN

    @property
    def import_patterns(self) -> list[str]:
        return [
            r"from\s+langchain",
            r"import\s+langchain",
            r"from\s+langchain_community",
            r"from\s+langchain_openai",
            r"from\s+langchain_anthropic",
            r"from\s+langchain_core",
        ]

    def _extract_components(
        self, tree: ast.Module, source: str, file: Path, root: Path
    ) -> list[Component]:
        """Extract LangChain components from AST."""
        components: list[Component] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = self._get_call_name(node)
                if name and name in LANGCHAIN_COMPONENT_MAP:
                    component = self._create_component(
                        name=name,
                        node=node,
                        file=file,
                        root=root,
                        source=source,
                    )
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
        self,
        name: str,
        node: ast.Call,
        file: Path,
        root: Path,
        source: str,
    ) -> Component:
        """Create a Component from an AST Call node."""
        component_type = LANGCHAIN_COMPONENT_MAP[name]
        component_id = self._generate_id(name, file, node.lineno)

        # Try to extract model name from kwargs
        model_name = self._extract_model_name(node)
        provider = MODEL_PROVIDERS.get(name)

        return Component(
            id=component_id,
            name=name,
            component_type=component_type,
            source=ComponentSource(
                file=file.relative_to(root),
                line=node.lineno,
                framework=Framework.LANGCHAIN,
            ),
            model_name=model_name,
            provider=provider,
            properties=self._extract_properties(node),
        )

    def _extract_model_name(self, node: ast.Call) -> str | None:
        """Try to extract the model name from constructor arguments."""
        for keyword in node.keywords:
            if keyword.arg in ("model", "model_name") and isinstance(
                keyword.value, ast.Constant
            ):
                return str(keyword.value.value)
        # Check first positional argument
        if node.args and isinstance(node.args[0], ast.Constant):
            return str(node.args[0].value)
        return None

    def _extract_properties(self, node: ast.Call) -> dict[str, str]:
        """Extract notable properties from constructor kwargs."""
        props: dict[str, str] = {}
        for keyword in node.keywords:
            if keyword.arg in ("temperature", "max_tokens", "streaming"):
                if isinstance(keyword.value, ast.Constant):
                    props[keyword.arg] = str(keyword.value.value)
        return props

    def _generate_id(self, name: str, file: Path, line: int) -> str:
        """Generate a stable component ID."""
        raw = f"{file}:{line}:{name}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
