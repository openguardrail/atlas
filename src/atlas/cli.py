"""Atlas CLI - AI system discovery and risk mapping."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from atlas import __version__
from atlas.generators.cyclonedx import generate_bom
from atlas.graph.mapper import build_topology
from atlas.risk.classifier import classify_system
from atlas.scanners import scan_project

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="atlas")
def main() -> None:
    """Atlas - AI system discovery and risk mapping.

    Discover agentic AI architectures, map component relationships,
    classify risk, and generate CycloneDX AIBOMs.
    """


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path. Defaults to stdout.",
)
@click.option(
    "--format", "-f",
    "output_format",
    type=click.Choice(["json", "xml"]),
    default="json",
    help="Output format (json or xml).",
)
@click.option(
    "--risk/--no-risk",
    default=True,
    help="Include risk classification in output.",
)
def scan(path: Path, output: Path | None, output_format: str, risk: bool) -> None:
    """Scan a project directory for AI system components.

    Discovers models, agents, tools, vector stores, and their relationships.
    Outputs a CycloneDX AIBOM.
    """
    console.print(f"[bold blue]Atlas[/] scanning: {path}")

    # Discover AI components
    scan_result = scan_project(path)

    if not scan_result.components:
        console.print("[yellow]No AI system components detected.[/]")
        return

    console.print(f"[green]Found {len(scan_result.components)} components[/]")

    # Build dependency graph
    topology = build_topology(scan_result)

    # Classify risk if requested
    risk_assessment = None
    if risk:
        risk_assessment = classify_system(scan_result.components, topology)
        tier = risk_assessment.tier
        console.print(f"[bold]Risk tier:[/] {tier.value}")

    # Generate BOM
    bom_output = generate_bom(
        components=scan_result.components,
        topology=topology,
        risk_assessment=risk_assessment,
        output_format=output_format,
    )

    if output:
        output.write_text(bom_output)
        console.print(f"[green]AIBOM written to:[/] {output}")
    else:
        click.echo(bom_output)


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def graph(path: Path) -> None:
    """Display the AI system dependency graph.

    Shows components and their relationships in a visual tree.
    """
    console.print(f"[bold blue]Atlas[/] mapping dependencies: {path}")

    scan_result = scan_project(path)

    if not scan_result.components:
        console.print("[yellow]No AI system components detected.[/]")
        return

    topology = build_topology(scan_result)
    topology.print_tree(console)


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def risk(path: Path) -> None:
    """Assess the risk classification of an AI system.

    Classifies the system against EU AI Act, NIST AI RMF, and
    ISO/IEC 42001 risk categories. Identifies potential attack surfaces.
    """
    console.print(f"[bold blue]Atlas[/] assessing risk: {path}")

    scan_result = scan_project(path)

    if not scan_result.components:
        console.print("[yellow]No AI system components detected.[/]")
        return

    topology = build_topology(scan_result)
    assessment = classify_system(scan_result.components, topology)
    assessment.print_report(console)


if __name__ == "__main__":
    main()
