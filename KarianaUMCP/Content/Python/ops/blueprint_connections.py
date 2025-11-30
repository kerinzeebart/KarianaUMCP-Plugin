"""
KarianaUMCP Blueprint Connection Operations
============================================
Blueprint node pin discovery and auto-wiring tools.

Supports:
- get_blueprint_node_pins
- validate_blueprint_connection
- auto_connect_blueprint_chain
- suggest_blueprint_connections
- get_blueprint_graph_connections
"""

from typing import Dict, Any, List, Optional
import traceback


def handle_blueprint_connection_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route blueprint connection commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "get_blueprint_node_pins": get_blueprint_node_pins,
        "validate_blueprint_connection": validate_blueprint_connection,
        "auto_connect_blueprint_chain": auto_connect_blueprint_chain,
        "suggest_blueprint_connections": suggest_blueprint_connections,
        "get_blueprint_graph_connections": get_blueprint_graph_connections,
    }

    handler = handlers.get(cmd)
    if handler:
        try:
            return handler(data)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    else:
        return {"success": False, "error": f"Unknown blueprint connection command: {cmd}"}


def _load_blueprint(blueprint_path: str):
    """Helper to load a blueprint"""
    import unreal

    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    return unreal.load_asset(blueprint_path)


def _get_blueprint_graph(blueprint, function_name: str = "EventGraph"):
    """Helper to get a blueprint graph"""
    import unreal

    # Get all graphs from the blueprint
    try:
        graphs = blueprint.get_editor_property("ubergraph_pages")
        for graph in graphs:
            if graph.get_name() == function_name or function_name in str(graph.get_name()):
                return graph

        # If not found in ubergraph_pages, check function_graphs
        func_graphs = blueprint.get_editor_property("function_graphs")
        for graph in func_graphs:
            if graph.get_name() == function_name or function_name in str(graph.get_name()):
                return graph

    except Exception:
        pass

    return None


def get_blueprint_node_pins(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get all pins for a Blueprint node.

    Args:
        blueprint_path: Path to the Blueprint
        node_name: Name or GUID of the node
        function_name: Function graph name (default: "EventGraph")
    """
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    node_name = data.get("node_name", "") or data.get("node_id", "")
    function_name = data.get("function_name", "EventGraph") or data.get("function_id", "EventGraph")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}
    if not node_name:
        return {"success": False, "error": "node_name is required"}

    try:
        blueprint = _load_blueprint(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        graph = _get_blueprint_graph(blueprint, function_name)
        if not graph:
            return {"success": False, "error": f"Function graph not found: {function_name}"}

        # Get nodes from graph
        nodes = graph.get_editor_property("nodes")
        target_node = None

        for node in nodes:
            if node.get_name() == node_name or str(node.get_name()).endswith(node_name):
                target_node = node
                break

        if not target_node:
            return {"success": False, "error": f"Node not found: {node_name}"}

        # Get pins from node
        input_pins = []
        output_pins = []

        try:
            # Get all pins
            all_pins = target_node.get_editor_property("pins")

            for pin in all_pins:
                pin_info = {
                    "name": pin.get_name(),
                    "type": str(pin.get_editor_property("pin_type")),
                    "direction": "input" if pin.get_editor_property("direction") == 0 else "output",
                    "is_connected": len(pin.get_editor_property("linked_to")) > 0
                }

                if pin_info["direction"] == "input":
                    input_pins.append(pin_info)
                else:
                    output_pins.append(pin_info)

        except Exception as e:
            return {"success": False, "error": f"Failed to get pins: {e}"}

        return {
            "success": True,
            "node_name": node_name,
            "node_class": target_node.get_class().get_name(),
            "input_pins": input_pins,
            "output_pins": output_pins,
            "total_pins": len(input_pins) + len(output_pins)
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to get node pins: {e}"}


def validate_blueprint_connection(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a Blueprint node connection before making it.

    Args:
        blueprint_path: Path to the Blueprint
        source_node: Source node name
        source_pin: Source pin name
        target_node: Target node name
        target_pin: Target pin name
    """
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    source_node = data.get("source_node", "") or data.get("source_node_id", "")
    source_pin = data.get("source_pin", "") or data.get("source_pin_name", "")
    target_node = data.get("target_node", "") or data.get("target_node_id", "")
    target_pin = data.get("target_pin", "") or data.get("target_pin_name", "")

    if not all([blueprint_path, source_node, source_pin, target_node, target_pin]):
        return {"success": False, "error": "All parameters required: blueprint_path, source_node, source_pin, target_node, target_pin"}

    try:
        # Get pin information for both nodes
        source_result = get_blueprint_node_pins({
            "blueprint_path": blueprint_path,
            "node_name": source_node
        })

        if not source_result.get("success"):
            return {"success": False, "error": f"Source node error: {source_result.get('error')}"}

        target_result = get_blueprint_node_pins({
            "blueprint_path": blueprint_path,
            "node_name": target_node
        })

        if not target_result.get("success"):
            return {"success": False, "error": f"Target node error: {target_result.get('error')}"}

        # Find source pin in outputs
        source_pin_info = None
        for pin in source_result.get("output_pins", []):
            if pin["name"] == source_pin or source_pin in pin["name"]:
                source_pin_info = pin
                break

        # Find target pin in inputs
        target_pin_info = None
        for pin in target_result.get("input_pins", []):
            if pin["name"] == target_pin or target_pin in pin["name"]:
                target_pin_info = pin
                break

        if not source_pin_info:
            return {
                "success": True,
                "valid": False,
                "error_type": "PIN_NOT_FOUND",
                "message": f"Source output pin not found: {source_pin}",
                "available_output_pins": [p["name"] for p in source_result.get("output_pins", [])]
            }

        if not target_pin_info:
            return {
                "success": True,
                "valid": False,
                "error_type": "PIN_NOT_FOUND",
                "message": f"Target input pin not found: {target_pin}",
                "available_input_pins": [p["name"] for p in target_result.get("input_pins", [])]
            }

        # Basic type compatibility check
        source_type = source_pin_info.get("type", "")
        target_type = target_pin_info.get("type", "")

        # Simple validation - execution pins connect to execution, data to data
        is_exec_source = "exec" in source_type.lower()
        is_exec_target = "exec" in target_type.lower()

        if is_exec_source != is_exec_target:
            return {
                "success": True,
                "valid": False,
                "error_type": "TYPE_MISMATCH",
                "message": "Cannot connect execution pin to data pin",
                "source_type": source_type,
                "target_type": target_type
            }

        return {
            "success": True,
            "valid": True,
            "source_pin": source_pin_info,
            "target_pin": target_pin_info,
            "message": "Connection appears valid"
        }

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}


def auto_connect_blueprint_chain(data: Dict[str, Any]) -> Dict[str, Any]:
    """Automatically wire a chain of Blueprint nodes.

    Args:
        blueprint_path: Path to the Blueprint
        node_chain: List of node names to connect in sequence
        validate_before_connect: Validate before making connections (default True)
    """
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    node_chain = data.get("node_chain", [])
    validate_before = data.get("validate_before_connect", True)

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}
    if len(node_chain) < 2:
        return {"success": False, "error": "node_chain must contain at least 2 nodes"}

    try:
        blueprint = _load_blueprint(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        connections_made = []
        failed_connections = []
        warnings = []

        # Process pairs of nodes
        for i in range(len(node_chain) - 1):
            source_node = node_chain[i]
            target_node = node_chain[i + 1]

            # Get pins for both nodes
            source_pins = get_blueprint_node_pins({
                "blueprint_path": blueprint_path,
                "node_name": source_node
            })

            target_pins = get_blueprint_node_pins({
                "blueprint_path": blueprint_path,
                "node_name": target_node
            })

            if not source_pins.get("success") or not target_pins.get("success"):
                failed_connections.append({
                    "source": source_node,
                    "target": target_node,
                    "reason": "Failed to get pins"
                })
                continue

            # Try to find execution pins first
            exec_connected = False
            for out_pin in source_pins.get("output_pins", []):
                if "exec" in out_pin.get("type", "").lower() or out_pin.get("name") == "then":
                    for in_pin in target_pins.get("input_pins", []):
                        if "exec" in in_pin.get("type", "").lower() or in_pin.get("name") == "execute":
                            connections_made.append({
                                "source_node": source_node,
                                "source_pin": out_pin["name"],
                                "target_node": target_node,
                                "target_pin": in_pin["name"],
                                "connection_type": "execution"
                            })
                            exec_connected = True
                            break
                    if exec_connected:
                        break

            # Then try data pins (match by compatible types)
            data_connections = []
            for out_pin in source_pins.get("output_pins", []):
                if "exec" in out_pin.get("type", "").lower():
                    continue
                for in_pin in target_pins.get("input_pins", []):
                    if "exec" in in_pin.get("type", "").lower():
                        continue
                    # Simple type matching
                    if out_pin.get("type") == in_pin.get("type"):
                        data_connections.append({
                            "source_node": source_node,
                            "source_pin": out_pin["name"],
                            "target_node": target_node,
                            "target_pin": in_pin["name"],
                            "connection_type": "data"
                        })

            connections_made.extend(data_connections[:3])  # Limit to 3 data connections per pair

            if not exec_connected and not data_connections:
                warnings.append(f"No compatible pins found between {source_node} and {target_node}")

        return {
            "success": True,
            "connections_made": len(connections_made),
            "connections": connections_made,
            "failed_connections": failed_connections,
            "warnings": warnings,
            "message": f"Processed {len(node_chain)} nodes, made {len(connections_made)} connection suggestions"
        }

    except Exception as e:
        return {"success": False, "error": f"Auto-connect failed: {e}"}


def suggest_blueprint_connections(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get ranked connection suggestions between two nodes.

    Args:
        blueprint_path: Path to the Blueprint
        source_node: Source node name
        target_node: Target node name
    """
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    source_node = data.get("source_node", "") or data.get("source_node_id", "")
    target_node = data.get("target_node", "") or data.get("target_node_id", "")

    if not all([blueprint_path, source_node, target_node]):
        return {"success": False, "error": "blueprint_path, source_node, and target_node are required"}

    try:
        source_pins = get_blueprint_node_pins({
            "blueprint_path": blueprint_path,
            "node_name": source_node
        })

        target_pins = get_blueprint_node_pins({
            "blueprint_path": blueprint_path,
            "node_name": target_node
        })

        if not source_pins.get("success"):
            return source_pins
        if not target_pins.get("success"):
            return target_pins

        suggestions = []
        execution_connection = None

        # Find execution connections
        for out_pin in source_pins.get("output_pins", []):
            out_type = out_pin.get("type", "").lower()
            if "exec" in out_type or out_pin.get("name") in ["then", "Then", "execute", "Execute"]:
                for in_pin in target_pins.get("input_pins", []):
                    in_type = in_pin.get("type", "").lower()
                    if "exec" in in_type or in_pin.get("name") in ["execute", "Execute"]:
                        execution_connection = {
                            "source_pin": out_pin["name"],
                            "target_pin": in_pin["name"],
                            "confidence": 1.0,
                            "type": "execution"
                        }
                        break
                if execution_connection:
                    break

        # Find data connections
        data_connections = []
        for out_pin in source_pins.get("output_pins", []):
            out_type = out_pin.get("type", "")
            if "exec" in out_type.lower():
                continue

            for in_pin in target_pins.get("input_pins", []):
                in_type = in_pin.get("type", "")
                if "exec" in in_type.lower():
                    continue

                # Calculate confidence based on type match
                confidence = 0.0
                if out_type == in_type:
                    confidence = 1.0
                elif out_pin["name"].lower() == in_pin["name"].lower():
                    confidence = 0.8
                elif "object" in out_type.lower() and "object" in in_type.lower():
                    confidence = 0.5

                if confidence > 0:
                    data_connections.append({
                        "source_pin": out_pin["name"],
                        "target_pin": in_pin["name"],
                        "source_type": out_type,
                        "target_type": in_type,
                        "confidence": confidence,
                        "type": "data"
                    })

        # Sort by confidence
        data_connections.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "success": True,
            "source_node": source_node,
            "target_node": target_node,
            "execution_connection": execution_connection,
            "data_connections": data_connections[:5],
            "total_suggestions": len(data_connections) + (1 if execution_connection else 0)
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to get suggestions: {e}"}


def get_blueprint_graph_connections(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get all connections in a Blueprint function graph.

    Args:
        blueprint_path: Path to the Blueprint
        function_name: Function graph name (default: "EventGraph")
    """
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    function_name = data.get("function_name", "EventGraph") or data.get("function_id", "EventGraph")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    try:
        blueprint = _load_blueprint(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        graph = _get_blueprint_graph(blueprint, function_name)
        if not graph:
            return {"success": False, "error": f"Function graph not found: {function_name}"}

        connections = []
        nodes_info = []

        # Get all nodes
        nodes = graph.get_editor_property("nodes")

        for node in nodes:
            node_name = node.get_name()
            node_class = node.get_class().get_name()

            nodes_info.append({
                "name": node_name,
                "class": node_class
            })

            # Get pins and their connections
            try:
                pins = node.get_editor_property("pins")
                for pin in pins:
                    # Check if this is an output pin with connections
                    if pin.get_editor_property("direction") == 1:  # Output
                        linked_pins = pin.get_editor_property("linked_to")
                        for linked_pin in linked_pins:
                            target_node = linked_pin.get_outer()
                            connections.append({
                                "source_node": node_name,
                                "source_pin": pin.get_name(),
                                "target_node": target_node.get_name() if target_node else "unknown",
                                "target_pin": linked_pin.get_name()
                            })
            except Exception:
                pass

        return {
            "success": True,
            "blueprint_path": blueprint_path,
            "function_name": function_name,
            "nodes": nodes_info,
            "node_count": len(nodes_info),
            "connections": connections,
            "total_connections": len(connections)
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to get graph connections: {e}"}
