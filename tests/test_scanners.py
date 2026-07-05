"""Tests for Atlas scanners."""

from __future__ import annotations

from pathlib import Path

from atlas.models import ComponentType, Framework
from atlas.scanners import scan_project
from atlas.scanners.autogen_scanner import AutoGenScanner
from atlas.scanners.crewai_scanner import CrewAIScanner
from atlas.scanners.generic_scanner import GenericScanner
from atlas.scanners.langchain_scanner import LangChainScanner

LANGCHAIN_SAMPLE = """
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory

llm = ChatOpenAI(model="gpt-4", temperature=0.7)
agent = AgentExecutor(agent=react_agent, tools=tools)
vectorstore = Chroma(collection_name="docs")
memory = ConversationBufferMemory()
"""

CREWAI_SAMPLE = """
from crewai import Agent, Task, Crew

researcher = Agent(
    role="Senior Researcher",
    goal="Find the latest AI papers",
    backstory="You are a research assistant",
)
writer = Agent(
    role="Writer",
    goal="Write summaries",
)
crew = Crew(agents=[researcher, writer], tasks=[task1])
"""

AUTOGEN_SAMPLE = """
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

assistant = AssistantAgent(name="assistant", system_message="You help with coding")
user_proxy = UserProxyAgent(name="user_proxy", human_input_mode="NEVER")
group_chat = GroupChat(agents=[assistant, user_proxy], messages=[])
manager = GroupChatManager(groupchat=group_chat)
"""

GENERIC_SAMPLE = """
from openai import OpenAI
from chromadb import Client as ChromaClient

client = OpenAI(api_key="sk-xxx")
db = ChromaClient()
"""


def _write_sample(dir: Path, filename: str, content: str) -> Path:
    """Write sample code to a temp file."""
    file = dir / filename
    file.write_text(content)
    return file


class TestLangChainScanner:
    def test_detects_langchain_components(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "app.py", LANGCHAIN_SAMPLE)
        scanner = LangChainScanner()
        result = scanner.scan([tmp_path / "app.py"], tmp_path)

        assert len(result.components) >= 3
        assert result.frameworks_detected == [Framework.LANGCHAIN]

        types = {c.component_type for c in result.components}
        assert ComponentType.MODEL in types
        assert ComponentType.AGENT in types
        assert ComponentType.VECTOR_STORE in types

    def test_extracts_model_name(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "app.py", LANGCHAIN_SAMPLE)
        scanner = LangChainScanner()
        result = scanner.scan([tmp_path / "app.py"], tmp_path)

        models = [c for c in result.components if c.component_type == ComponentType.MODEL]
        assert len(models) >= 1
        assert models[0].model_name == "gpt-4"
        assert models[0].provider == "openai"


class TestCrewAIScanner:
    def test_detects_crewai_components(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "crew.py", CREWAI_SAMPLE)
        scanner = CrewAIScanner()
        result = scanner.scan([tmp_path / "crew.py"], tmp_path)

        assert len(result.components) >= 3
        assert result.frameworks_detected == [Framework.CREWAI]

        types = {c.component_type for c in result.components}
        assert ComponentType.AGENT in types
        assert ComponentType.ORCHESTRATOR in types


class TestAutoGenScanner:
    def test_detects_autogen_components(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "multi_agent.py", AUTOGEN_SAMPLE)
        scanner = AutoGenScanner()
        result = scanner.scan([tmp_path / "multi_agent.py"], tmp_path)

        assert len(result.components) >= 3
        assert result.frameworks_detected == [Framework.AUTOGEN]

        types = {c.component_type for c in result.components}
        assert ComponentType.AGENT in types
        assert ComponentType.ORCHESTRATOR in types

    def test_extracts_agent_name(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "multi_agent.py", AUTOGEN_SAMPLE)
        scanner = AutoGenScanner()
        result = scanner.scan([tmp_path / "multi_agent.py"], tmp_path)

        agents = [c for c in result.components if c.component_type == ComponentType.AGENT]
        agent_names = {a.name for a in agents}
        assert "assistant" in agent_names
        assert "user_proxy" in agent_names


class TestGenericScanner:
    def test_detects_openai_client(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "app.py", GENERIC_SAMPLE)
        scanner = GenericScanner()
        result = scanner.scan([tmp_path / "app.py"], tmp_path)

        assert len(result.components) >= 1
        types = {c.component_type for c in result.components}
        assert ComponentType.VECTOR_STORE in types


class TestScanProject:
    def test_full_scan(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "langchain_app.py", LANGCHAIN_SAMPLE)
        _write_sample(tmp_path, "crew.py", CREWAI_SAMPLE)

        result = scan_project(tmp_path)

        assert len(result.components) >= 5
        assert Framework.LANGCHAIN in result.frameworks_detected
        assert Framework.CREWAI in result.frameworks_detected

    def test_empty_project(self, tmp_path: Path) -> None:
        _write_sample(tmp_path, "hello.py", "print('hello')")

        result = scan_project(tmp_path)
        assert len(result.components) == 0
