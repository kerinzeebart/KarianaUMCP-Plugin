"""
KarianaUMCP Validation Operations
=================================
Actor and placement validation tools.

Supports:
- validate_actor_spawn
- validate_actor_location
- validate_actor_rotation
- validate_actor_scale
- validate_actor_exists
- validate_actor_deleted
- validate_placement
"""

from typing import Dict, Any, List, Optional
import traceback


def handle_validation_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route validation commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "validate_actor_spawn": validate_actor_spawn,
        "validate_actor_location": validate_actor_location,
        "validate_actor_rotation": validate_actor_rotation,
        "validate_actor_scale": validate_actor_scale,
        "validate_actor_exists": validate_actor_exists,
        "validate_actor_deleted": validate_actor_deleted,
        "validate_placement": validate_placement,
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
        return {"success": False, "error": f"Unknown validation command: {cmd}"}


def _find_actor_by_name(actor_name: str):
    """Helper to find actor by label"""
    import unreal
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in actors:
        if actor.get_actor_label() == actor_name:
            return actor
    return None


def _vectors_equal(v1, v2, tolerance: float = 0.1) -> bool:
    """Check if two vectors are approximately equal"""
    return (abs(v1[0] - v2[0]) < tolerance and
            abs(v1[1] - v2[1]) < tolerance and
            abs(v1[2] - v2[2]) < tolerance)


def validate_actor_spawn(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that an actor was spawned correctly.

    Args:
        actor_name: Name of the spawned actor
        expected_class: Expected actor class (optional)
        expected_location: Expected [X, Y, Z] location (optional)
        tolerance: Position tolerance (default 1.0)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    expected_class = data.get("expected_class")
    expected_location = data.get("expected_location")
    tolerance = data.get("tolerance", 1.0)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)

        if not actor:
            return {
                "success": True,
                "valid": False,
                "error_type": "ACTOR_NOT_FOUND",
                "message": f"Actor '{actor_name}' was not found in the level"
            }

        result = {
            "success": True,
            "valid": True,
            "actor_name": actor_name,
            "actor_class": actor.get_class().get_name(),
            "checks": []
        }

        # Validate class if specified
        if expected_class:
            actual_class = actor.get_class().get_name()
            class_match = expected_class.lower() in actual_class.lower()
            result["checks"].append({
                "check": "class",
                "passed": class_match,
                "expected": expected_class,
                "actual": actual_class
            })
            if not class_match:
                result["valid"] = False

        # Validate location if specified
        if expected_location:
            actual_loc = actor.get_actor_location()
            actual = [actual_loc.x, actual_loc.y, actual_loc.z]
            location_match = _vectors_equal(expected_location, actual, tolerance)
            result["checks"].append({
                "check": "location",
                "passed": location_match,
                "expected": expected_location,
                "actual": actual,
                "tolerance": tolerance
            })
            if not location_match:
                result["valid"] = False

        result["message"] = "Spawn validated successfully" if result["valid"] else "Spawn validation failed"
        return result

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}


def validate_actor_location(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an actor's location.

    Args:
        actor_name: Name of the actor
        expected_location: Expected [X, Y, Z] location
        tolerance: Position tolerance (default 0.1)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    expected_location = data.get("expected_location", [])
    tolerance = data.get("tolerance", 0.1)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}
    if not expected_location or len(expected_location) < 3:
        return {"success": False, "error": "expected_location [X, Y, Z] is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        actual_loc = actor.get_actor_location()
        actual = [actual_loc.x, actual_loc.y, actual_loc.z]

        location_match = _vectors_equal(expected_location, actual, tolerance)

        delta = [
            actual[0] - expected_location[0],
            actual[1] - expected_location[1],
            actual[2] - expected_location[2]
        ]

        return {
            "success": True,
            "valid": location_match,
            "actor_name": actor_name,
            "expected": expected_location,
            "actual": actual,
            "delta": delta,
            "tolerance": tolerance,
            "message": "Location validated" if location_match else "Location mismatch"
        }

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}


def validate_actor_rotation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an actor's rotation.

    Args:
        actor_name: Name of the actor
        expected_rotation: Expected [Pitch, Yaw, Roll] rotation
        tolerance: Rotation tolerance in degrees (default 0.1)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    expected_rotation = data.get("expected_rotation", [])
    tolerance = data.get("tolerance", 0.1)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}
    if not expected_rotation or len(expected_rotation) < 3:
        return {"success": False, "error": "expected_rotation [Pitch, Yaw, Roll] is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        actual_rot = actor.get_actor_rotation()
        actual = [actual_rot.pitch, actual_rot.yaw, actual_rot.roll]

        rotation_match = _vectors_equal(expected_rotation, actual, tolerance)

        return {
            "success": True,
            "valid": rotation_match,
            "actor_name": actor_name,
            "expected": expected_rotation,
            "actual": actual,
            "tolerance": tolerance,
            "message": "Rotation validated" if rotation_match else "Rotation mismatch"
        }

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}


def validate_actor_scale(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an actor's scale.

    Args:
        actor_name: Name of the actor
        expected_scale: Expected [X, Y, Z] scale
        tolerance: Scale tolerance (default 0.01)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    expected_scale = data.get("expected_scale", [])
    tolerance = data.get("tolerance", 0.01)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}
    if not expected_scale or len(expected_scale) < 3:
        return {"success": False, "error": "expected_scale [X, Y, Z] is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        actual_scale = actor.get_actor_scale3d()
        actual = [actual_scale.x, actual_scale.y, actual_scale.z]

        scale_match = _vectors_equal(expected_scale, actual, tolerance)

        return {
            "success": True,
            "valid": scale_match,
            "actor_name": actor_name,
            "expected": expected_scale,
            "actual": actual,
            "tolerance": tolerance,
            "message": "Scale validated" if scale_match else "Scale mismatch"
        }

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}


def validate_actor_exists(data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify that an actor exists in the level.

    Args:
        actor_name: Name of the actor
    """
    actor_name = data.get("actor_name", "")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        exists = actor is not None

        result = {
            "success": True,
            "valid": exists,
            "actor_name": actor_name,
            "exists": exists,
            "message": f"Actor '{actor_name}' {'exists' if exists else 'does not exist'}"
        }

        if exists:
            result["actor_class"] = actor.get_class().get_name()
            loc = actor.get_actor_location()
            result["location"] = [loc.x, loc.y, loc.z]

        return result

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}


def validate_actor_deleted(data: Dict[str, Any]) -> Dict[str, Any]:
    """Verify that an actor has been deleted from the level.

    Args:
        actor_name: Name of the actor that should be deleted
    """
    actor_name = data.get("actor_name", "")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        deleted = actor is None

        return {
            "success": True,
            "valid": deleted,
            "actor_name": actor_name,
            "deleted": deleted,
            "message": f"Actor '{actor_name}' {'was deleted' if deleted else 'still exists'}"
        }

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}


def validate_placement(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate actor placement relative to grid or other actors.

    Args:
        actor_name: Name of the actor
        grid_size: Expected grid alignment size (optional)
        min_distance_from_others: Minimum distance from other actors (optional)
        allowed_overlap: Whether overlapping is allowed (default False)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    grid_size = data.get("grid_size")
    min_distance = data.get("min_distance_from_others")
    allowed_overlap = data.get("allowed_overlap", False)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        loc = actor.get_actor_location()
        checks = []
        all_valid = True

        # Grid alignment check
        if grid_size and grid_size > 0:
            x_aligned = abs(loc.x % grid_size) < 0.1 or abs(loc.x % grid_size - grid_size) < 0.1
            y_aligned = abs(loc.y % grid_size) < 0.1 or abs(loc.y % grid_size - grid_size) < 0.1
            z_aligned = abs(loc.z % grid_size) < 0.1 or abs(loc.z % grid_size - grid_size) < 0.1

            grid_aligned = x_aligned and y_aligned and z_aligned
            checks.append({
                "check": "grid_alignment",
                "passed": grid_aligned,
                "grid_size": grid_size,
                "offsets": {
                    "x": loc.x % grid_size,
                    "y": loc.y % grid_size,
                    "z": loc.z % grid_size
                }
            })
            if not grid_aligned:
                all_valid = False

        # Distance check from other actors
        if min_distance:
            all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
            too_close = []

            for other in all_actors:
                if not other or other == actor:
                    continue
                other_loc = other.get_actor_location()
                distance = ((loc.x - other_loc.x)**2 +
                           (loc.y - other_loc.y)**2 +
                           (loc.z - other_loc.z)**2) ** 0.5

                if distance < min_distance:
                    too_close.append({
                        "actor": other.get_actor_label(),
                        "distance": distance
                    })

            distance_ok = len(too_close) == 0
            checks.append({
                "check": "min_distance",
                "passed": distance_ok,
                "min_distance": min_distance,
                "violations": too_close[:5]  # Limit to 5
            })
            if not distance_ok:
                all_valid = False

        # Overlap check
        if not allowed_overlap:
            bounds = actor.get_actor_bounds(False)
            origin, extent = bounds

            all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
            overlapping = []

            for other in all_actors:
                if not other or other == actor:
                    continue
                other_bounds = other.get_actor_bounds(False)
                other_origin, other_extent = other_bounds

                # Simple AABB overlap check
                overlap_x = (abs(origin.x - other_origin.x) < (extent.x + other_extent.x))
                overlap_y = (abs(origin.y - other_origin.y) < (extent.y + other_extent.y))
                overlap_z = (abs(origin.z - other_origin.z) < (extent.z + other_extent.z))

                if overlap_x and overlap_y and overlap_z:
                    overlapping.append(other.get_actor_label())

            no_overlap = len(overlapping) == 0
            checks.append({
                "check": "overlap",
                "passed": no_overlap,
                "overlapping_actors": overlapping[:5]  # Limit to 5
            })
            if not no_overlap:
                all_valid = False

        return {
            "success": True,
            "valid": all_valid,
            "actor_name": actor_name,
            "location": [loc.x, loc.y, loc.z],
            "checks": checks,
            "message": "Placement valid" if all_valid else "Placement issues found"
        }

    except Exception as e:
        return {"success": False, "error": f"Validation failed: {e}"}
