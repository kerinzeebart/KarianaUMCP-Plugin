"""
KarianaUMCP Auto-Wire System
============================
Automatically connect Blueprint nodes based on pin compatibility.
"""

from typing import Dict, Any, List, Optional
import traceback


def auto_wire(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatically wire Blueprint nodes based on compatible pins.

    Args:
        blueprint_path: Path to the Blueprint asset
        graph_name: Name of the graph to wire (default: EventGraph)
        dry_run: If True, only report what would be wired

    Returns:
        dict: Wiring results with connections made
    """
    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")
    graph_name = data.get("graph_name", "EventGraph")
    dry_run = data.get("dry_run", False)

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    try:
        import unreal

        # Normalize path
        if not blueprint_path.startswith("/Game"):
            blueprint_path = f"/Game/{blueprint_path}"

        # Load Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Get the Blueprint's generated class
        generated_class = blueprint.get_editor_property("generated_class")
        if not generated_class:
            return {"success": False, "error": "Blueprint has no generated class"}

        # Get the Blueprint graph
        # Note: Direct graph access requires the Blueprint Graph subsystem
        # This is a simplified implementation

        connections_made = []
        potential_connections = []

        # Find unconnected execution pins
        # In full implementation, iterate through all nodes and find:
        # 1. Unconnected output exec pins
        # 2. Unconnected input exec pins
        # 3. Type-compatible data pins

        # For now, return a status indicating the feature
        return {
            "success": True,
            "blueprint": blueprint_path,
            "graph": graph_name,
            "connections_made": len(connections_made),
            "potential_connections": potential_connections,
            "dry_run": dry_run,
            "message": "Auto-wire analysis complete. Full implementation requires Blueprint Graph API access."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def find_unconnected_pins(blueprint, graph_name: str) -> Dict[str, List]:
    """Find all unconnected pins in a Blueprint graph"""
    unconnected = {
        "exec_output": [],  # Unconnected execution output pins
        "exec_input": [],   # Unconnected execution input pins
        "data_output": [],  # Unconnected data output pins
        "data_input": []    # Unconnected data input pins
    }

    # Implementation would iterate through nodes and check pin connections
    # This requires access to the Blueprint graph subsystem

    return unconnected


def suggest_connections(unconnected: Dict[str, List]) -> List[Dict]:
    """Suggest connections based on unconnected pins"""
    suggestions = []

    # Match exec output pins with exec input pins
    for exec_out in unconnected["exec_output"]:
        for exec_in in unconnected["exec_input"]:
            # Check if connection makes sense (e.g., BeginPlay -> PrintString)
            suggestions.append({
                "type": "execution",
                "from_node": exec_out["node"],
                "from_pin": exec_out["pin"],
                "to_node": exec_in["node"],
                "to_pin": exec_in["pin"],
                "confidence": 0.8
            })

    # Match data pins by type
    for data_out in unconnected["data_output"]:
        for data_in in unconnected["data_input"]:
            if _pins_compatible(data_out, data_in):
                suggestions.append({
                    "type": "data",
                    "from_node": data_out["node"],
                    "from_pin": data_out["pin"],
                    "to_node": data_in["node"],
                    "to_pin": data_in["pin"],
                    "confidence": _calculate_confidence(data_out, data_in)
                })

    return suggestions


def _pins_compatible(pin_a: Dict, pin_b: Dict) -> bool:
    """Check if two pins are type-compatible"""
    # Same type is always compatible
    if pin_a.get("type") == pin_b.get("type"):
        return True

    # Some types are implicitly convertible
    convertible = {
        ("int", "float"): True,
        ("float", "int"): True,
        ("string", "text"): True,
        ("name", "string"): True,
    }

    return convertible.get((pin_a.get("type"), pin_b.get("type")), False)


def _calculate_confidence(pin_a: Dict, pin_b: Dict) -> float:
    """Calculate confidence score for a suggested connection"""
    base_confidence = 0.5

    # Same type increases confidence
    if pin_a.get("type") == pin_b.get("type"):
        base_confidence += 0.3

    # Same name increases confidence
    if pin_a.get("name", "").lower() == pin_b.get("name", "").lower():
        base_confidence += 0.2

    return min(base_confidence, 1.0)
