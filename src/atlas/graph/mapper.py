"""AI system dependency mapper - builds directed graph of component relationships."""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
from rich.console import Console
from rich.tree import Tree

from atlas.models import Component, ComponentType, Relationship, ScanResult


@dataclass
class Topology:
    """Represents the AI system topology as a directed graph."""

    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    components_by_id: dict[str, Component] = field(default_factory=dict)

    def add_component(self, component: Component) -> None:
        """Add a component as a node in the graph."""
        self.graph.add_node(
            component.id,
            name=component.name,
            type=component.component_type.value,
            framework=component.source.framework.value,
        )
        self.components_by_id[component.id] = component

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship as an edge in the graph."""
        if relationship.source_id in self.graph and relationship.target_id in self.graph:
            self.graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                relationship_type=relationship.relationship_type,
            )

    @property
    def roots(self) -> list[str]:
        """Get root nodes (nodes with no incoming edges)."""
        return [n for n in self.graph.nodes if self.graph.in_degree(n) == 0]

    @property
    def leaves(self) -> list[str]:
        """Get leaf nodes (nodes with no outgoing edges)."""
        return [n for n in self.graph.nodes if self.graph.out_degree(n) == 0]

    @property
    def depth(self) -> int:
        """Maximum depth of the dependency graph."""
        if not self.graph.nodes:
            return 0
        try:
            return nx.dag_longest_path_length(self.graph) + 1
        except nx.NetworkXUnfeasible:
            # Graph has cycles - depth is undefined, return 0
            return 0

    def print_tree(self, console: Console) -> None:
        """Print the dependency graph as a tree from root to leaf."""
        if not self.graph.nodes:
            console.print("[yellow]Empty graph - no components found.[/]")
            return

        # Find roots (entry points with no incoming edges)
        roots = self.roots
        if not roots:
            # If no clear roots (cycles), pick orchestrators or agents
            roots = [
                c.id for c in self.components_by_id.values()
                if c.component_type in (ComponentType.ORCHESTRATOR, ComponentType.AGENT)
            ]
        if not roots:
            roots = list(self.graph.nodes)[:1]

        if len(roots) == 1:
            root_name = self.components_by_id[roots[0]].name
        else:
            root_name = "System"
        tree = Tree(f"[bold blue]{root_name}[/]")

        visited: set[str] = set()

        def _add_node(parent_tree: Tree, node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)

            comp = self.components_by_id.get(node_id)
            if not comp:
                return

            label = f"{comp.name} [dim][{comp.component_type.value}][/]"
            if comp.provider:
                label += f" [dim]({comp.provider})[/]"

            branch = parent_tree.add(label)

            for successor in self.graph.successors(node_id):
                _add_node(branch, successor)

        for root_id in roots:
            if len(roots) == 1:
                # Single root - add its children directly to tree
                visited.add(root_id)
                comp = self.components_by_id.get(root_id)
                if comp:
                    tree.label = f"[bold blue]{comp.name}[/] [dim][{comp.component_type.value}][/]"
                for successor in self.graph.successors(root_id):
                    _add_node(tree, successor)
            else:
                _add_node(tree, root_id)

        console.print(tree)
        console.print(
            f"\n[bold]{len(self.graph.nodes)}[/] components | "
            f"[bold]{len(self.graph.edges)}[/] dependencies | "
            f"depth: [bold]{self.depth}[/]"
        )


def build_topology(scan_result: ScanResult | list[Component]) -> Topology:
    """Build a topology graph from scan results.

    Infers relationships between components based on:
    - Explicit relationships from scanners
    - Co-location in the same file
    - Type-based heuristics (agents use models, chains use retrievers, etc.)

    Args:
        scan_result: Scan result or list of components.

    Returns:
        Topology graph.
    """
    if isinstance(scan_result, ScanResult):
        components = scan_result.components
        relationships = scan_result.relationships
    else:
        components = scan_result
        relationships = []
        for comp in components:
            relationships.extend(comp.relationships)

    topology = Topology()

    # Add all components as nodes
    for component in components:
        topology.add_component(component)

    # Add explicit relationships
    for rel in relationships:
        topology.add_relationship(rel)

    # Infer relationships based on type heuristics
    _infer_relationships(topology, components)

    return topology


def _infer_relationships(topology: Topology, components: list[Component]) -> None:
    """Infer relationships between components based on type patterns.

    Common AI system patterns:
    - Orchestrators connect to agents
    - Agents use models and tools
    - Chains use models and retrievers
    - Retrievers connect to vector stores
    """
    # Index components by type
    by_type: dict[ComponentType, list[Component]] = {}
    for comp in components:
        by_type.setdefault(comp.component_type, []).append(comp)

    # Index components by file for co-location
    by_file: dict[str, list[Component]] = {}
    for comp in components:
        file_key = str(comp.source.file)
        by_file.setdefault(file_key, []).append(comp)

    # Orchestrators → Agents (same file only)
    for file_key, file_components in by_file.items():
        orchestrators_in_file = [
            c for c in file_components if c.component_type == ComponentType.ORCHESTRATOR
        ]
        agents_in_file = [
            c for c in file_components if c.component_type == ComponentType.AGENT
        ]
        for orchestrator in orchestrators_in_file:
            for agent in agents_in_file:
                topology.add_relationship(Relationship(
                    source_id=orchestrator.id,
                    target_id=agent.id,
                    relationship_type="orchestrates",
                ))

    # Agents → Models and Tools (same file)
    for file_key, file_components in by_file.items():
        agents_in_file = [c for c in file_components if c.component_type == ComponentType.AGENT]
        models_in_file = [c for c in file_components if c.component_type == ComponentType.MODEL]
        tools_in_file = [c for c in file_components if c.component_type == ComponentType.TOOL]

        for agent in agents_in_file:
            for model in models_in_file:
                topology.add_relationship(Relationship(
                    source_id=agent.id,
                    target_id=model.id,
                    relationship_type="uses",
                ))
            for tool in tools_in_file:
                topology.add_relationship(Relationship(
                    source_id=agent.id,
                    target_id=tool.id,
                    relationship_type="calls",
                ))

    # Chains → Models
    for chain in by_type.get(ComponentType.CHAIN, []):
        for model in by_type.get(ComponentType.MODEL, []):
            if str(chain.source.file) == str(model.source.file):
                topology.add_relationship(Relationship(
                    source_id=chain.id,
                    target_id=model.id,
                    relationship_type="uses",
                ))

    # Retrievers → Vector Stores
    for retriever in by_type.get(ComponentType.RETRIEVER, []):
        for vs in by_type.get(ComponentType.VECTOR_STORE, []):
            topology.add_relationship(Relationship(
                source_id=retriever.id,
                target_id=vs.id,
                relationship_type="retrieves_from",
            ))
