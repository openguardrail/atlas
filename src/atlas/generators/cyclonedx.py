"""CycloneDX AIBOM generator."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring

from atlas import __version__
from atlas.models import Component, ComponentType, ScanResult

if TYPE_CHECKING:
    from atlas.graph.mapper import Topology
    from atlas.risk.classifier import RiskAssessment


# Map our component types to CycloneDX types
CYCLONEDX_TYPE_MAP: dict[ComponentType, str] = {
    ComponentType.MODEL: "machine-learning-model",
    ComponentType.AGENT: "application",
    ComponentType.TOOL: "library",
    ComponentType.VECTOR_STORE: "data",
    ComponentType.ORCHESTRATOR: "framework",
    ComponentType.GUARDRAIL: "library",
    ComponentType.DATA_SOURCE: "data",
    ComponentType.API_ENDPOINT: "service",
    ComponentType.MEMORY: "data",
    ComponentType.PROMPT_TEMPLATE: "data",
    ComponentType.RETRIEVER: "library",
    ComponentType.CHAIN: "framework",
    ComponentType.ROUTER: "framework",
}


def generate_bom(
    components: ScanResult | list[Component],
    topology: Topology | None = None,
    risk_assessment: RiskAssessment | None = None,
    output_format: str = "json",
) -> str:
    """Generate a CycloneDX AIBOM from discovered components.

    Args:
        components: Scan result or list of components.
        topology: Optional topology graph.
        risk_assessment: Optional risk assessment to include.
        output_format: Output format ("json" or "xml").

    Returns:
        CycloneDX BOM as a string.
    """
    if isinstance(components, ScanResult):
        component_list = components.components
    else:
        component_list = components

    if output_format == "json":
        return _generate_json(component_list, topology, risk_assessment)
    elif output_format == "xml":
        return _generate_xml(component_list, topology, risk_assessment)
    else:
        raise ValueError(f"Unsupported format: {output_format}")


def _generate_json(
    components: list[Component],
    topology: Topology | None,
    risk_assessment: RiskAssessment | None,
) -> str:
    """Generate CycloneDX JSON format."""
    bom: dict = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "openguardrail-atlas",
                        "version": __version__,
                        "supplier": {
                            "name": "OpenGuardrail",
                            "url": ["https://github.com/openguardrail"],
                        },
                    }
                ]
            },
        },
        "components": [],
        "dependencies": [],
    }

    for component in components:
        cdx_component = _component_to_cdx_json(component)
        bom["components"].append(cdx_component)

    # Add dependencies from topology
    if topology:
        for node_id in topology.graph.nodes:
            successors = list(topology.graph.successors(node_id))
            if successors:
                bom["dependencies"].append({
                    "ref": node_id,
                    "dependsOn": successors,
                })

    # Add risk assessment as a property
    if risk_assessment:
        bom["metadata"]["properties"] = [
            {
                "name": "atlas:risk:tier",
                "value": risk_assessment.tier.value,
            },
            {
                "name": "atlas:risk:score",
                "value": str(risk_assessment.score),
            },
        ]

    return json.dumps(bom, indent=2)


def _generate_xml(
    components: list[Component],
    topology: Topology | None,
    risk_assessment: RiskAssessment | None,
) -> str:
    """Generate CycloneDX XML format."""
    bom = Element("bom")
    bom.set("xmlns", "http://cyclonedx.org/schema/bom/1.6")
    bom.set("serialNumber", f"urn:uuid:{uuid.uuid4()}")
    bom.set("version", "1")

    # Metadata
    metadata = SubElement(bom, "metadata")
    timestamp = SubElement(metadata, "timestamp")
    timestamp.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    tools = SubElement(metadata, "tools")
    tools_components = SubElement(tools, "components")
    tool_component = SubElement(tools_components, "component")
    tool_component.set("type", "application")
    tool_name = SubElement(tool_component, "name")
    tool_name.text = "openguardrail-atlas"
    tool_version = SubElement(tool_component, "version")
    tool_version.text = __version__

    # Risk properties
    if risk_assessment:
        properties = SubElement(metadata, "properties")
        prop_tier = SubElement(properties, "property")
        prop_tier.set("name", "atlas:risk:tier")
        prop_tier.text = risk_assessment.tier.value
        prop_score = SubElement(properties, "property")
        prop_score.set("name", "atlas:risk:score")
        prop_score.text = str(risk_assessment.score)

    # Components
    components_elem = SubElement(bom, "components")
    for component in components:
        _component_to_cdx_xml(component, components_elem)

    # Dependencies
    if topology:
        dependencies_elem = SubElement(bom, "dependencies")
        for node_id in topology.graph.nodes:
            successors = list(topology.graph.successors(node_id))
            if successors:
                dep = SubElement(dependencies_elem, "dependency")
                dep.set("ref", node_id)
                for successor in successors:
                    child_dep = SubElement(dep, "dependency")
                    child_dep.set("ref", successor)

    # Pretty print
    raw_xml = tostring(bom, encoding="unicode")
    dom = parseString(raw_xml)
    return dom.toprettyxml(indent="  ", encoding=None)


def _component_to_cdx_json(component: Component) -> dict:
    """Convert an atlas Component to CycloneDX JSON component."""
    cdx_type = CYCLONEDX_TYPE_MAP.get(component.component_type, "library")

    cdx: dict = {
        "type": cdx_type,
        "bom-ref": component.id,
        "name": component.name,
    }

    if component.version:
        cdx["version"] = component.version

    if component.description:
        cdx["description"] = component.description

    if component.provider:
        cdx["supplier"] = {"name": component.provider}

    # Add model card for ML model components
    if component.component_type == ComponentType.MODEL:
        model_card: dict = {}
        if component.model_name:
            model_card["modelParameters"] = {
                "task": "inference",
                "modelArchitecture": component.model_name,
            }
        if model_card:
            cdx["modelCard"] = model_card

    # Properties
    if component.properties:
        cdx["properties"] = [
            {"name": f"atlas:{k}", "value": v} for k, v in component.properties.items()
        ]

    # Source location
    cdx.setdefault("properties", [])
    cdx["properties"].append({
        "name": "atlas:source:file",
        "value": str(component.source.file),
    })
    cdx["properties"].append({
        "name": "atlas:source:line",
        "value": str(component.source.line),
    })
    cdx["properties"].append({
        "name": "atlas:source:framework",
        "value": component.source.framework.value,
    })

    return cdx


def _component_to_cdx_xml(component: Component, parent: Element) -> None:
    """Convert an atlas Component to CycloneDX XML element."""
    cdx_type = CYCLONEDX_TYPE_MAP.get(component.component_type, "library")

    elem = SubElement(parent, "component")
    elem.set("type", cdx_type)
    elem.set("bom-ref", component.id)

    name = SubElement(elem, "name")
    name.text = component.name

    if component.version:
        version = SubElement(elem, "version")
        version.text = component.version

    if component.description:
        desc = SubElement(elem, "description")
        desc.text = component.description

    if component.provider:
        supplier = SubElement(elem, "supplier")
        supplier_name = SubElement(supplier, "name")
        supplier_name.text = component.provider

    # Properties
    properties = SubElement(elem, "properties")
    prop_file = SubElement(properties, "property")
    prop_file.set("name", "atlas:source:file")
    prop_file.text = str(component.source.file)

    prop_line = SubElement(properties, "property")
    prop_line.set("name", "atlas:source:line")
    prop_line.text = str(component.source.line)

    prop_fw = SubElement(properties, "property")
    prop_fw.set("name", "atlas:source:framework")
    prop_fw.text = component.source.framework.value

    for k, v in component.properties.items():
        prop = SubElement(properties, "property")
        prop.set("name", f"atlas:{k}")
        prop.text = v
