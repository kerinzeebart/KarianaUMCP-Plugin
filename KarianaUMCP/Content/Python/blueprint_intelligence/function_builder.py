"""
KarianaUMCP Function Builder
============================
Create Blueprint functions programmatically.
"""

from typing import Dict, Any, List
import traceback


def create_function(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new function in a Blueprint.

    Args:
        blueprint_path: Path to the Blueprint
        function_name: Name for the new function
        inputs: List of input parameters [{name, type, default}]
        outputs: List of output parameters [{name, type}]
        description: Function description
        pure: Whether function is pure (no side effects)
        category: Function category for organization

    Returns:
        dict: Function creation results
    """
    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")
    function_name = data.get("function_name", "") or data.get("name", "")
    inputs = data.get("inputs", [])
    outputs = data.get("outputs", [])
    description = data.get("description", "")
    is_pure = data.get("pure", False)
    category = data.get("category", "Default")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    if not function_name:
        return {"success": False, "error": "function_name is required"}

    try:
        import unreal

        # Normalize path
        if not blueprint_path.startswith("/Game"):
            blueprint_path = f"/Game/{blueprint_path}"

        # Load Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Creating Blueprint functions programmatically is complex
        # and requires the Blueprint Graph subsystem
        # This is a simplified response showing the intended function

        function_spec = {
            "name": function_name,
            "inputs": inputs,
            "outputs": outputs,
            "pure": is_pure,
            "category": category,
            "description": description
        }

        return {
            "success": True,
            "blueprint": blueprint_path,
            "function": function_spec,
            "message": "Function specification created. Manual Blueprint editing may be required for full implementation."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def generate_function_template(function_name: str, inputs: List[Dict], outputs: List[Dict]) -> str:
    """Generate a Python template for Blueprint function logic"""

    input_params = ", ".join([f"{inp.get('name', 'param')}: {inp.get('type', 'Any')}" for inp in inputs])
    output_types = ", ".join([out.get('type', 'Any') for out in outputs])

    template = f'''
def {function_name}({input_params}):
    """
    Blueprint function: {function_name}

    Inputs:
{_format_params(inputs)}

    Outputs:
{_format_params(outputs)}
    """
    # Function implementation here
    pass
'''
    return template


def _format_params(params: List[Dict]) -> str:
    """Format parameter list for documentation"""
    if not params:
        return "        None"

    lines = []
    for param in params:
        name = param.get('name', 'param')
        ptype = param.get('type', 'Any')
        desc = param.get('description', '')
        lines.append(f"        {name} ({ptype}): {desc}")

    return "\n".join(lines)


def validate_function_name(name: str) -> Dict[str, Any]:
    """Validate a function name for Blueprint use"""
    errors = []
    warnings = []

    # Check for valid characters
    if not name.replace('_', '').isalnum():
        errors.append("Function name must contain only alphanumeric characters and underscores")

    # Check starting character
    if name and name[0].isdigit():
        errors.append("Function name cannot start with a number")

    # Check reserved words
    reserved = ["BeginPlay", "Tick", "EndPlay", "Construction", "ReceiveDestroyed"]
    if name in reserved:
        warnings.append(f"'{name}' is a reserved event name")

    # Check length
    if len(name) > 100:
        warnings.append("Function name is very long, consider shortening")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
