"""
KarianaUMCP Error Handling
==========================
Structured error responses for UMCP tools following MCP best practices.
"""
from typing import Any, Dict, Optional
from enum import IntEnum


class ErrorCode(IntEnum):
    """
    Standard MCP error codes plus custom UMCP codes.

    MCP Standard Codes (-32xxx):
    - PARSE_ERROR: Invalid JSON
    - INVALID_REQUEST: Invalid request structure
    - METHOD_NOT_FOUND: Unknown method/tool
    - INVALID_PARAMS: Invalid method parameters
    - INTERNAL_ERROR: Server error

    UMCP Custom Codes (-32001 to -32099):
    - ACTOR_NOT_FOUND: Actor doesn't exist
    - ASSET_NOT_FOUND: Asset doesn't exist
    - BLUEPRINT_ERROR: Blueprint operation failed
    - VALIDATION_ERROR: Input validation failed
    - UNREAL_ERROR: Unreal Engine API error
    - TIMEOUT_ERROR: Operation timed out
    - AUTH_ERROR: Authentication failed
    """
    # MCP Standard Codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # UMCP Custom Codes
    ACTOR_NOT_FOUND = -32001
    ASSET_NOT_FOUND = -32002
    BLUEPRINT_ERROR = -32003
    VALIDATION_ERROR = -32004
    UNREAL_ERROR = -32005
    TIMEOUT_ERROR = -32006
    AUTH_ERROR = -32007
    LEVEL_ERROR = -32008
    MATERIAL_ERROR = -32009
    VIEWPORT_ERROR = -32010


def make_error(
    code: ErrorCode,
    message: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a structured error response.

    Args:
        code: Error code from ErrorCode enum
        message: Human-readable error message
        data: Optional additional error data

    Returns:
        Structured error response dict

    Example:
        >>> make_error(ErrorCode.ACTOR_NOT_FOUND, "Actor 'Cube' not found", {"actor_name": "Cube"})
        {
            "success": False,
            "error": {
                "code": -32001,
                "message": "Actor 'Cube' not found",
                "data": {"actor_name": "Cube"}
            }
        }
    """
    return {
        "success": False,
        "error": {
            "code": int(code),
            "message": message,
            "data": data or {}
        }
    }


def make_success(
    data: Any = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a structured success response.

    Args:
        data: Response data (any serializable type)
        message: Optional human-readable message

    Returns:
        Structured success response dict

    Example:
        >>> make_success({"actor_name": "Cube_0", "location": [0, 0, 0]}, "Actor spawned")
        {
            "success": True,
            "data": {"actor_name": "Cube_0", "location": [0, 0, 0]},
            "message": "Actor spawned"
        }
    """
    response = {
        "success": True,
        "data": data
    }
    if message:
        response["message"] = message
    return response


def wrap_error(
    exception: Exception,
    code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    context: Optional[str] = None,
    include_type: bool = True
) -> Dict[str, Any]:
    """
    Wrap an exception into a structured error response.
    Does NOT include traceback for security reasons.

    Args:
        exception: The exception that was caught
        code: Error code to use
        context: Optional context about what was being attempted
        include_type: Whether to include exception type in response

    Returns:
        Structured error response dict
    """
    message = str(exception)[:200]  # Limit message length

    if context:
        message = f"{context}: {message}"

    data = {}
    if include_type:
        data["exception_type"] = type(exception).__name__

    return make_error(code, message, data if data else None)


# Convenience functions for common error types
def actor_not_found(actor_name: str, available: Optional[list] = None) -> Dict[str, Any]:
    """Create an actor not found error."""
    data = {"actor_name": actor_name}
    if available:
        data["available_actors"] = available[:10]  # Limit to 10 suggestions
    return make_error(
        ErrorCode.ACTOR_NOT_FOUND,
        f"Actor not found: {actor_name}",
        data
    )


def asset_not_found(asset_path: str) -> Dict[str, Any]:
    """Create an asset not found error."""
    return make_error(
        ErrorCode.ASSET_NOT_FOUND,
        f"Asset not found: {asset_path}",
        {"asset_path": asset_path}
    )


def validation_error(
    message: str,
    field: Optional[str] = None,
    expected: Optional[Any] = None,
    received: Optional[Any] = None
) -> Dict[str, Any]:
    """Create a validation error."""
    data = {}
    if field:
        data["field"] = field
    if expected is not None:
        data["expected"] = expected
    if received is not None:
        data["received"] = str(received)[:100]  # Limit length

    return make_error(ErrorCode.VALIDATION_ERROR, message, data if data else None)


def missing_required(fields: list) -> Dict[str, Any]:
    """Create a missing required fields error."""
    return make_error(
        ErrorCode.INVALID_PARAMS,
        f"Missing required fields: {', '.join(fields)}",
        {"missing_fields": fields}
    )


def invalid_enum(value: Any, field: str, allowed: list) -> Dict[str, Any]:
    """Create an invalid enum value error."""
    return make_error(
        ErrorCode.VALIDATION_ERROR,
        f"Invalid {field}: '{value}'",
        {
            "field": field,
            "received": str(value),
            "allowed_values": allowed
        }
    )


def unreal_error(message: str, operation: Optional[str] = None) -> Dict[str, Any]:
    """Create an Unreal Engine error."""
    data = {}
    if operation:
        data["operation"] = operation
    return make_error(ErrorCode.UNREAL_ERROR, message, data if data else None)
