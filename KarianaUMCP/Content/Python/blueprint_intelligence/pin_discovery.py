"""
KarianaUMCP Pin Discovery
=========================
Discover compatible pins for Blueprint nodes.
"""

from typing import Dict, Any, List
import traceback


def find_pins(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find compatible pins for a given node.

    Args:
        blueprint_path: Path to the Blueprint
        node_name: Name of the node to analyze
        pin_name: Specific pin to find compatible connections for

    Returns:
        dict: Compatible pins information
    """
    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")
    node_name = data.get("node_name", "")
    pin_name = data.get("pin_name", "")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    if not node_name:
        return {"success": False, "error": "node_name is required"}

    try:
        import unreal

        # Normalize path
        if not blueprint_path.startswith("/Game"):
            blueprint_path = f"/Game/{blueprint_path}"

        # Load Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Common pin types and their compatible connections
        common_pins = get_common_pin_info(node_name)

        return {
            "success": True,
            "blueprint": blueprint_path,
            "node": node_name,
            "pins": common_pins,
            "message": "Pin discovery complete"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def get_common_pin_info(node_name: str) -> Dict[str, Any]:
    """Get common pin information for known node types"""

    # Common Blueprint node types and their pins
    node_pins = {
        "BeginPlay": {
            "outputs": [
                {"name": "exec", "type": "exec", "description": "Execution output"}
            ],
            "inputs": []
        },
        "Tick": {
            "outputs": [
                {"name": "exec", "type": "exec", "description": "Execution output"},
                {"name": "DeltaTime", "type": "float", "description": "Time since last tick"}
            ],
            "inputs": []
        },
        "PrintString": {
            "inputs": [
                {"name": "exec", "type": "exec", "description": "Execution input"},
                {"name": "InString", "type": "string", "description": "String to print"},
                {"name": "bPrintToScreen", "type": "bool", "description": "Print to screen"},
                {"name": "bPrintToLog", "type": "bool", "description": "Print to log"},
                {"name": "TextColor", "type": "LinearColor", "description": "Text color"},
                {"name": "Duration", "type": "float", "description": "Display duration"}
            ],
            "outputs": [
                {"name": "exec", "type": "exec", "description": "Execution output"}
            ]
        },
        "SpawnActor": {
            "inputs": [
                {"name": "exec", "type": "exec", "description": "Execution input"},
                {"name": "Class", "type": "class", "description": "Actor class to spawn"},
                {"name": "SpawnTransform", "type": "Transform", "description": "Spawn location/rotation"},
                {"name": "CollisionHandling", "type": "enum", "description": "Collision handling"}
            ],
            "outputs": [
                {"name": "exec", "type": "exec", "description": "Execution output"},
                {"name": "ReturnValue", "type": "Actor", "description": "Spawned actor reference"}
            ]
        },
        "GetActorLocation": {
            "inputs": [
                {"name": "Target", "type": "Actor", "description": "Actor to get location of"}
            ],
            "outputs": [
                {"name": "ReturnValue", "type": "Vector", "description": "Actor location"}
            ]
        },
        "SetActorLocation": {
            "inputs": [
                {"name": "exec", "type": "exec", "description": "Execution input"},
                {"name": "Target", "type": "Actor", "description": "Actor to move"},
                {"name": "NewLocation", "type": "Vector", "description": "New location"},
                {"name": "bSweep", "type": "bool", "description": "Sweep for collision"},
                {"name": "bTeleport", "type": "bool", "description": "Teleport physics"}
            ],
            "outputs": [
                {"name": "exec", "type": "exec", "description": "Execution output"},
                {"name": "SweepHitResult", "type": "HitResult", "description": "Hit result if sweep"}
            ]
        },
        "Branch": {
            "inputs": [
                {"name": "exec", "type": "exec", "description": "Execution input"},
                {"name": "Condition", "type": "bool", "description": "Branch condition"}
            ],
            "outputs": [
                {"name": "True", "type": "exec", "description": "True branch"},
                {"name": "False", "type": "exec", "description": "False branch"}
            ]
        },
        "ForEachLoop": {
            "inputs": [
                {"name": "exec", "type": "exec", "description": "Execution input"},
                {"name": "Array", "type": "array", "description": "Array to iterate"}
            ],
            "outputs": [
                {"name": "LoopBody", "type": "exec", "description": "Loop body execution"},
                {"name": "ArrayElement", "type": "wildcard", "description": "Current element"},
                {"name": "ArrayIndex", "type": "int", "description": "Current index"},
                {"name": "Completed", "type": "exec", "description": "Loop completed"}
            ]
        },
        "Delay": {
            "inputs": [
                {"name": "exec", "type": "exec", "description": "Execution input"},
                {"name": "Duration", "type": "float", "description": "Delay duration in seconds"}
            ],
            "outputs": [
                {"name": "Completed", "type": "exec", "description": "After delay"}
            ]
        }
    }

    # Return pins for known node types
    for key in node_pins:
        if key.lower() in node_name.lower():
            return node_pins[key]

    # Default unknown node
    return {
        "inputs": [{"name": "exec", "type": "exec", "description": "Execution input (assumed)"}],
        "outputs": [{"name": "exec", "type": "exec", "description": "Execution output (assumed)"}],
        "note": "Node type not recognized - showing assumed pins"
    }


def get_compatible_types(pin_type: str) -> List[str]:
    """Get list of types compatible with the given pin type"""

    compatibility = {
        "exec": ["exec"],
        "bool": ["bool"],
        "int": ["int", "float", "byte"],
        "float": ["float", "int", "double"],
        "string": ["string", "name", "text"],
        "name": ["name", "string"],
        "text": ["text", "string"],
        "Vector": ["Vector", "Vector2D"],
        "Rotator": ["Rotator"],
        "Transform": ["Transform"],
        "Actor": ["Actor", "Pawn", "Character"],
        "Object": ["Object", "Actor", "Component"],
    }

    return compatibility.get(pin_type, [pin_type])
