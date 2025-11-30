"""
KarianaUMCP Input Validation
============================
Comprehensive input validation utilities for UMCP tools.
"""
from typing import Any, Dict, List, Optional, Tuple, Union
from errors import make_error, ErrorCode, validation_error, missing_required, invalid_enum


# =============================================================================
# Enum Constants
# =============================================================================

# Actor classes that can be spawned
ACTOR_CLASSES = [
    "StaticMeshActor", "PointLight", "SpotLight", "DirectionalLight",
    "RectLight", "SkyLight", "CameraActor", "CineCameraActor",
    "PlayerStart", "TargetPoint", "Note",
    "TriggerBox", "TriggerSphere", "TriggerCapsule",
    "BlockingVolume", "PostProcessVolume", "LightmassImportanceVolume",
    "SphereReflectionCapture", "BoxReflectionCapture", "PlanarReflectionCapture",
    "ExponentialHeightFog", "SkyAtmosphere", "VolumetricCloud",
    "AudioVolume", "ReverbVolume",
    "DecalActor", "TextRenderActor",
    "Emitter", "NiagaraActor"
]

# Viewport render modes
RENDER_MODES = [
    "lit", "unlit", "wireframe", "detail_lighting",
    "lighting_only", "light_complexity", "shader_complexity",
    "lightmap_density", "stationary_light_overlap"
]

# Viewport view modes
VIEW_MODES = [
    "perspective", "top", "bottom", "left", "right", "front", "back",
    "orthographic"
]

# Blueprint parent classes
BLUEPRINT_PARENTS = [
    "Actor", "Pawn", "Character", "PlayerController", "AIController",
    "GameModeBase", "GameStateBase", "PlayerState",
    "ActorComponent", "SceneComponent",
    "UserWidget", "HUD"
]

# Component types for blueprints
COMPONENT_TYPES = [
    "StaticMeshComponent", "SkeletalMeshComponent",
    "PointLightComponent", "SpotLightComponent", "DirectionalLightComponent",
    "CameraComponent", "SpringArmComponent",
    "AudioComponent", "NiagaraComponent", "ParticleSystemComponent",
    "BoxComponent", "SphereComponent", "CapsuleComponent",
    "ArrowComponent", "BillboardComponent", "TextRenderComponent",
    "SceneComponent", "ChildActorComponent",
    "WidgetComponent", "DecalComponent"
]

# Asset types
ASSET_TYPES = [
    "StaticMesh", "SkeletalMesh", "Texture2D", "Material",
    "MaterialInstance", "Blueprint", "SoundWave", "SoundCue",
    "AnimSequence", "AnimMontage", "NiagaraSystem", "ParticleSystem"
]

# Log severity levels
LOG_SEVERITIES = ["all", "error", "warning", "display", "log", "verbose"]


# =============================================================================
# Core Validators
# =============================================================================

def validate_required(
    data: Dict[str, Any],
    fields: List[str]
) -> Tuple[bool, Optional[Dict]]:
    """
    Validate that required fields are present and non-empty.

    Args:
        data: Input data dictionary
        fields: List of required field names

    Returns:
        Tuple of (is_valid, error_response or None)
    """
    missing = []
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)

    if missing:
        return False, missing_required(missing)
    return True, None


def validate_vector3(
    value: Any,
    name: str = "vector",
    allow_none: bool = False,
    default: Optional[List[float]] = None
) -> Tuple[bool, Optional[List[float]], Optional[Dict]]:
    """
    Validate a 3-component vector (location, rotation, scale).

    Args:
        value: Value to validate
        name: Field name for error messages
        allow_none: If True, None returns default value
        default: Default value if allow_none is True

    Returns:
        Tuple of (is_valid, validated_value, error_response or None)
    """
    if value is None:
        if allow_none:
            return True, default or [0.0, 0.0, 0.0], None
        return False, None, validation_error(
            f"{name} is required",
            field=name,
            expected="[x, y, z]",
            received="null"
        )

    if not isinstance(value, (list, tuple)):
        return False, None, validation_error(
            f"{name} must be an array",
            field=name,
            expected="[x, y, z]",
            received=type(value).__name__
        )

    if len(value) != 3:
        return False, None, validation_error(
            f"{name} must have exactly 3 components",
            field=name,
            expected=3,
            received=len(value)
        )

    try:
        result = [float(v) for v in value]
        return True, result, None
    except (ValueError, TypeError) as e:
        return False, None, validation_error(
            f"{name} components must be numbers",
            field=name,
            expected="[number, number, number]",
            received=str(value)
        )


def validate_vector4(
    value: Any,
    name: str = "color",
    allow_none: bool = False,
    default: Optional[List[float]] = None
) -> Tuple[bool, Optional[List[float]], Optional[Dict]]:
    """
    Validate a 4-component vector (RGBA color).

    Args:
        value: Value to validate
        name: Field name for error messages
        allow_none: If True, None returns default value
        default: Default value if allow_none is True

    Returns:
        Tuple of (is_valid, validated_value, error_response or None)
    """
    if value is None:
        if allow_none:
            return True, default or [1.0, 1.0, 1.0, 1.0], None
        return False, None, validation_error(
            f"{name} is required",
            field=name,
            expected="[r, g, b, a]"
        )

    if not isinstance(value, (list, tuple)):
        return False, None, validation_error(
            f"{name} must be an array",
            field=name,
            expected="[r, g, b, a]",
            received=type(value).__name__
        )

    if len(value) not in (3, 4):
        return False, None, validation_error(
            f"{name} must have 3 or 4 components",
            field=name,
            expected="[r, g, b] or [r, g, b, a]",
            received=len(value)
        )

    try:
        result = [float(v) for v in value]
        if len(result) == 3:
            result.append(1.0)  # Default alpha
        return True, result, None
    except (ValueError, TypeError):
        return False, None, validation_error(
            f"{name} components must be numbers",
            field=name
        )


def validate_enum(
    value: Any,
    allowed: List[str],
    name: str,
    case_sensitive: bool = False
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Validate value is in allowed enum values.

    Args:
        value: Value to validate
        allowed: List of allowed values
        name: Field name for error messages
        case_sensitive: Whether comparison is case-sensitive

    Returns:
        Tuple of (is_valid, normalized_value, error_response or None)
    """
    if value is None:
        return False, None, validation_error(
            f"{name} is required",
            field=name,
            expected=f"one of: {allowed}"
        )

    str_value = str(value)

    if case_sensitive:
        if str_value in allowed:
            return True, str_value, None
    else:
        # Case-insensitive match, return the canonical form
        for item in allowed:
            if item.lower() == str_value.lower():
                return True, item, None

    return False, None, invalid_enum(value, name, allowed)


def validate_range(
    value: Any,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    name: str = "value",
    allow_none: bool = False,
    default: Optional[float] = None
) -> Tuple[bool, Optional[float], Optional[Dict]]:
    """
    Validate numeric value is within range.

    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        name: Field name for error messages
        allow_none: If True, None returns default value
        default: Default value if allow_none is True

    Returns:
        Tuple of (is_valid, validated_value, error_response or None)
    """
    if value is None:
        if allow_none:
            return True, default, None
        return False, None, validation_error(
            f"{name} is required",
            field=name
        )

    try:
        num = float(value)
    except (ValueError, TypeError):
        return False, None, validation_error(
            f"{name} must be a number",
            field=name,
            received=type(value).__name__
        )

    if min_val is not None and num < min_val:
        return False, None, validation_error(
            f"{name} must be >= {min_val}",
            field=name,
            expected=f">= {min_val}",
            received=num
        )

    if max_val is not None and num > max_val:
        return False, None, validation_error(
            f"{name} must be <= {max_val}",
            field=name,
            expected=f"<= {max_val}",
            received=num
        )

    return True, num, None


def validate_string(
    value: Any,
    name: str,
    min_length: int = 0,
    max_length: int = 1000,
    pattern: Optional[str] = None,
    allow_none: bool = False,
    default: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Validate a string value.

    Args:
        value: Value to validate
        name: Field name for error messages
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Optional regex pattern to match
        allow_none: If True, None returns default value
        default: Default value if allow_none is True

    Returns:
        Tuple of (is_valid, validated_value, error_response or None)
    """
    if value is None:
        if allow_none:
            return True, default, None
        return False, None, validation_error(
            f"{name} is required",
            field=name
        )

    str_value = str(value).strip()

    if len(str_value) < min_length:
        return False, None, validation_error(
            f"{name} must be at least {min_length} characters",
            field=name,
            expected=f">= {min_length} chars",
            received=len(str_value)
        )

    if len(str_value) > max_length:
        return False, None, validation_error(
            f"{name} must be at most {max_length} characters",
            field=name,
            expected=f"<= {max_length} chars",
            received=len(str_value)
        )

    if pattern:
        import re
        if not re.match(pattern, str_value):
            return False, None, validation_error(
                f"{name} format is invalid",
                field=name,
                expected=f"matching pattern: {pattern}"
            )

    return True, str_value, None


def validate_asset_path(
    path: Any,
    name: str = "path",
    allow_none: bool = False
) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Validate and normalize an asset path.

    Args:
        path: Path to validate
        name: Field name for error messages
        allow_none: If True, None is valid

    Returns:
        Tuple of (is_valid, normalized_path, error_response or None)
    """
    if path is None:
        if allow_none:
            return True, None, None
        return False, None, validation_error(
            f"{name} is required",
            field=name
        )

    str_path = str(path).strip()

    # Check for path traversal
    if ".." in str_path:
        return False, None, validation_error(
            "Path traversal not allowed",
            field=name,
            received=str_path
        )

    # Normalize path to /Game/ format
    if not str_path.startswith("/"):
        str_path = "/" + str_path

    if not str_path.startswith("/Game/"):
        if str_path.startswith("/Content/"):
            str_path = "/Game/" + str_path[9:]
        elif str_path.startswith("/"):
            str_path = "/Game" + str_path
        else:
            str_path = "/Game/" + str_path

    return True, str_path, None


def validate_bool(
    value: Any,
    name: str,
    allow_none: bool = False,
    default: bool = False
) -> Tuple[bool, Optional[bool], Optional[Dict]]:
    """
    Validate a boolean value.

    Args:
        value: Value to validate
        name: Field name for error messages
        allow_none: If True, None returns default value
        default: Default value if allow_none is True

    Returns:
        Tuple of (is_valid, validated_value, error_response or None)
    """
    if value is None:
        if allow_none:
            return True, default, None
        return False, None, validation_error(
            f"{name} is required",
            field=name,
            expected="boolean"
        )

    if isinstance(value, bool):
        return True, value, None

    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes", "on"):
            return True, True, None
        if value.lower() in ("false", "0", "no", "off"):
            return True, False, None

    if isinstance(value, (int, float)):
        return True, bool(value), None

    return False, None, validation_error(
        f"{name} must be a boolean",
        field=name,
        expected="true/false",
        received=type(value).__name__
    )


# =============================================================================
# Composite Validators
# =============================================================================

def validate_actor_spawn(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
    """
    Validate all parameters for actor spawning.

    Args:
        data: Input data with actor_class, location, rotation, scale, name

    Returns:
        Tuple of (is_valid, validated_data, error_response or None)
    """
    validated = {}

    # Actor class (required, but has default)
    actor_class = data.get("actor_class", "StaticMeshActor")
    ok, actor_class, err = validate_enum(actor_class, ACTOR_CLASSES, "actor_class")
    if not ok:
        return False, None, err
    validated["actor_class"] = actor_class

    # Location (optional, defaults to origin)
    ok, location, err = validate_vector3(
        data.get("location"), "location", allow_none=True, default=[0.0, 0.0, 0.0]
    )
    if not ok:
        return False, None, err
    validated["location"] = location

    # Rotation (optional, defaults to zero)
    ok, rotation, err = validate_vector3(
        data.get("rotation"), "rotation", allow_none=True, default=[0.0, 0.0, 0.0]
    )
    if not ok:
        return False, None, err
    validated["rotation"] = rotation

    # Scale (optional, defaults to 1,1,1)
    ok, scale, err = validate_vector3(
        data.get("scale"), "scale", allow_none=True, default=[1.0, 1.0, 1.0]
    )
    if not ok:
        return False, None, err
    validated["scale"] = scale

    # Name (optional)
    if data.get("name"):
        ok, name, err = validate_string(
            data["name"], "name", min_length=1, max_length=100,
            pattern=r"^[A-Za-z0-9_]+$"
        )
        if not ok:
            return False, None, err
        validated["name"] = name

    return True, validated, None


def validate_blueprint_create(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
    """
    Validate all parameters for blueprint creation.

    Args:
        data: Input data with name, path, parent_class

    Returns:
        Tuple of (is_valid, validated_data, error_response or None)
    """
    validated = {}

    # Name (required)
    ok, err = validate_required(data, ["name"])
    if not ok:
        return False, None, err

    ok, name, err = validate_string(
        data["name"], "name", min_length=1, max_length=100,
        pattern=r"^[A-Za-z][A-Za-z0-9_]*$"
    )
    if not ok:
        return False, None, err
    validated["name"] = name

    # Path (optional)
    if data.get("path"):
        ok, path, err = validate_asset_path(data["path"], "path")
        if not ok:
            return False, None, err
        validated["path"] = path

    # Parent class (optional, defaults to Actor)
    parent_class = data.get("parent_class", "Actor")
    ok, parent_class, err = validate_enum(parent_class, BLUEPRINT_PARENTS, "parent_class")
    if not ok:
        return False, None, err
    validated["parent_class"] = parent_class

    return True, validated, None


def validate_screenshot(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
    """
    Validate screenshot capture parameters.

    Args:
        data: Input data with width, height, quality

    Returns:
        Tuple of (is_valid, validated_data, error_response or None)
    """
    validated = {}

    # Width (optional, defaults to 800)
    ok, width, err = validate_range(
        data.get("width"), min_val=320, max_val=4096, name="width",
        allow_none=True, default=800
    )
    if not ok:
        return False, None, err
    validated["width"] = int(width)

    # Height (optional, defaults to 600)
    ok, height, err = validate_range(
        data.get("height"), min_val=240, max_val=2160, name="height",
        allow_none=True, default=600
    )
    if not ok:
        return False, None, err
    validated["height"] = int(height)

    # Quality (optional, defaults to 85)
    ok, quality, err = validate_range(
        data.get("quality"), min_val=1, max_val=100, name="quality",
        allow_none=True, default=85
    )
    if not ok:
        return False, None, err
    validated["quality"] = int(quality)

    return True, validated, None
