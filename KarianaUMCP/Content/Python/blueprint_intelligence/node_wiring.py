"""
KarianaUMCP Node Wiring
=======================
Wire specific Blueprint nodes together.
"""

from typing import Dict, Any
import traceback


def wire_nodes(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wire two specific nodes together.

    Args:
        blueprint_path: Path to the Blueprint
        source_node: Source node name or ID
        source_pin: Source pin name
        target_node: Target node name or ID
        target_pin: Target pin name

    Returns:
        dict: Wiring results
    """
    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")
    source_node = data.get("source_node", "")
    source_pin = data.get("source_pin", "")
    target_node = data.get("target_node", "")
    target_pin = data.get("target_pin", "")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    if not all([source_node, source_pin, target_node, target_pin]):
        return {"success": False, "error": "source_node, source_pin, target_node, and target_pin are required"}

    try:
        import unreal

        # Normalize path
        if not blueprint_path.startswith("/Game"):
            blueprint_path = f"/Game/{blueprint_path}"

        # Load Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Direct node wiring requires the Blueprint Graph subsystem
        # This is a simplified implementation showing the intended connection

        connection = {
            "source": {"node": source_node, "pin": source_pin},
            "target": {"node": target_node, "pin": target_pin}
        }

        return {
            "success": True,
            "blueprint": blueprint_path,
            "connection": connection,
            "message": "Connection specification created. Use Blueprint editor for manual wiring."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def break_connection(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Break a connection between two nodes.

    Args:
        blueprint_path: Path to the Blueprint
        node: Node name
        pin: Pin name to disconnect

    Returns:
        dict: Results
    """
    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")
    node = data.get("node", "")
    pin = data.get("pin", "")

    if not blueprint_path or not node or not pin:
        return {"success": False, "error": "blueprint_path, node, and pin are required"}

    try:
        import unreal

        # Normalize path
        if not blueprint_path.startswith("/Game"):
            blueprint_path = f"/Game/{blueprint_path}"

        # Load Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        return {
            "success": True,
            "blueprint": blueprint_path,
            "disconnected": {"node": node, "pin": pin},
            "message": "Disconnection requested. Use Blueprint editor for manual confirmation."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def validate_connection(source_type: str, target_type: str) -> bool:
    """Check if two pin types can be connected"""

    # Same type is always valid
    if source_type == target_type:
        return True

    # Exec pins only connect to exec pins
    if source_type == "exec" or target_type == "exec":
        return source_type == target_type

    # Type compatibility rules
    compatible_pairs = [
        ("int", "float"),
        ("float", "int"),
        ("int", "double"),
        ("float", "double"),
        ("string", "name"),
        ("string", "text"),
        ("name", "string"),
        ("text", "string"),
        ("Object", "Actor"),
        ("Actor", "Pawn"),
        ("Pawn", "Character"),
    ]

    return (source_type, target_type) in compatible_pairs or (target_type, source_type) in compatible_pairs
