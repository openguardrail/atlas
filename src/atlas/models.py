"""Data models for discovered AI system components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ComponentType(Enum):
    """Types of AI system components."""

    MODEL = "model"
    AGENT = "agent"
    TOOL = "tool"
    VECTOR_STORE = "vector-store"
    ORCHESTRATOR = "orchestrator"
    GUARDRAIL = "guardrail"
    DATA_SOURCE = "data-source"
    API_ENDPOINT = "api-endpoint"
    MEMORY = "memory"
    PROMPT_TEMPLATE = "prompt-template"
    RETRIEVER = "retriever"
    CHAIN = "chain"
    ROUTER = "router"


class Framework(Enum):
    """Supported AI frameworks."""

    LANGCHAIN = "langchain"
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    LLAMAINDEX = "llamaindex"
    PYDANTIC_AI = "pydantic-ai"
    CUSTOM = "custom"


@dataclass
class ComponentSource:
    """Where a component was discovered."""

    file: Path
    line: int
    framework: Framework


@dataclass
class Relationship:
    """A relationship between two components."""

    source_id: str
    target_id: str
    relationship_type: str  # "uses", "calls", "retrieves_from", "routes_to", "validates"


@dataclass
class Component:
    """A discovered AI system component."""

    id: str
    name: str
    component_type: ComponentType
    source: ComponentSource
    version: str | None = None
    description: str | None = None
    model_name: str | None = None  # for MODEL type: e.g., "gpt-4", "llama-3"
    provider: str | None = None  # e.g., "openai", "anthropic", "huggingface"
    properties: dict[str, str] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result of scanning a project."""

    components: list[Component]
    relationships: list[Relationship]
    frameworks_detected: list[Framework]
    scan_path: Path
