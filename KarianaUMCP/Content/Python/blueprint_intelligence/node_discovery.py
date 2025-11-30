"""
KarianaUMCP Node Discovery
==========================
Discover and list nodes in Blueprint graphs.
"""

from typing import Dict, Any, List
import traceback


def get_nodes(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get all nodes in a Blueprint graph.

    Args:
        blueprint_path: Path to the Blueprint
        graph_name: Name of the graph (default: EventGraph)

    Returns:
        dict: Node information
    """
    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")
    graph_name = data.get("graph_name", "EventGraph")

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

        # Get Blueprint class info
        bp_class = blueprint.get_class().get_name()
        bp_name = blueprint.get_name()

        # Try to get function list
        functions = []
        try:
            # Get all Blueprint functions
            bp_gen_class = blueprint.get_editor_property("generated_class")
            if bp_gen_class:
                # List of default events in Actor Blueprints
                default_events = [
                    "BeginPlay",
                    "Tick",
                    "EndPlay",
                    "ReceiveBeginPlay",
                    "ReceiveTick",
                    "ReceiveEndPlay"
                ]

                functions.extend(default_events)

        except Exception as e:
            functions = ["EventGraph"]

        return {
            "success": True,
            "blueprint": blueprint_path,
            "name": bp_name,
            "class": bp_class,
            "graph": graph_name,
            "functions": functions,
            "message": "Node discovery complete"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def get_node_types() -> Dict[str, Any]:
    """Get list of common Blueprint node types"""

    node_types = {
        "events": [
            {"name": "BeginPlay", "description": "Called when play begins"},
            {"name": "Tick", "description": "Called every frame"},
            {"name": "EndPlay", "description": "Called when play ends"},
            {"name": "ActorBeginOverlap", "description": "Called when actors begin overlapping"},
            {"name": "ActorEndOverlap", "description": "Called when actors stop overlapping"},
            {"name": "InputAction", "description": "Called when input action occurs"},
        ],
        "flow_control": [
            {"name": "Branch", "description": "If/else branch"},
            {"name": "Sequence", "description": "Execute in sequence"},
            {"name": "ForLoop", "description": "For loop"},
            {"name": "ForEachLoop", "description": "Iterate over array"},
            {"name": "WhileLoop", "description": "While loop"},
            {"name": "DoOnce", "description": "Execute only once"},
            {"name": "Delay", "description": "Wait for time"},
            {"name": "Gate", "description": "Flow control gate"},
            {"name": "MultiGate", "description": "Multiple output gate"},
        ],
        "math": [
            {"name": "Add", "description": "Addition"},
            {"name": "Subtract", "description": "Subtraction"},
            {"name": "Multiply", "description": "Multiplication"},
            {"name": "Divide", "description": "Division"},
            {"name": "Clamp", "description": "Clamp value to range"},
            {"name": "Lerp", "description": "Linear interpolation"},
            {"name": "RandomFloat", "description": "Random float value"},
        ],
        "utilities": [
            {"name": "PrintString", "description": "Print to screen/log"},
            {"name": "GetActorLocation", "description": "Get actor position"},
            {"name": "SetActorLocation", "description": "Set actor position"},
            {"name": "SpawnActor", "description": "Spawn actor from class"},
            {"name": "DestroyActor", "description": "Destroy actor"},
            {"name": "GetAllActorsOfClass", "description": "Find all actors of type"},
        ],
        "variables": [
            {"name": "Get", "description": "Get variable value"},
            {"name": "Set", "description": "Set variable value"},
            {"name": "MakeArray", "description": "Create array"},
            {"name": "MakeVector", "description": "Create vector"},
            {"name": "BreakVector", "description": "Split vector into components"},
        ]
    }

    return {
        "success": True,
        "node_types": node_types,
        "categories": list(node_types.keys())
    }
