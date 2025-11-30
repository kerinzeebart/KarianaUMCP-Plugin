"""
KarianaUMCP Actor Operations
============================
Battle-tested actor manipulation tools (95%+ verified).

Supports:
- spawn_actor
- delete_actor
- list_actors
- get_actor_location
- set_actor_location
- set_actor_rotation
- set_actor_scale
- modify_actor_property
"""

from typing import Dict, Any, List, Optional
import traceback


def handle_actor_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route actor commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "spawn_actor": spawn_actor,
        "delete_actor": delete_actor,
        "list_actors": list_actors,
        "get_actor_location": get_actor_location,
        "set_actor_location": set_actor_location,
        "set_actor_rotation": set_actor_rotation,
        "set_actor_scale": set_actor_scale,
        "modify_actor_property": modify_actor_property,
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
        return {"success": False, "error": f"Unknown actor command: {cmd}"}


def spawn_actor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Spawn an actor in the level"""
    import unreal

    actor_class = data.get("actor_class", "StaticMeshActor")
    location = data.get("location", [0, 0, 0])
    rotation = data.get("rotation", [0, 0, 0])
    scale = data.get("scale", [1, 1, 1])
    name = data.get("name", "")

    # Validate parameters
    if not actor_class:
        return {"success": False, "error": "actor_class is required"}

    # Ensure location/rotation/scale are lists
    if isinstance(location, (list, tuple)) and len(location) >= 3:
        loc = unreal.Vector(float(location[0]), float(location[1]), float(location[2]))
    else:
        loc = unreal.Vector(0, 0, 0)

    if isinstance(rotation, (list, tuple)) and len(rotation) >= 3:
        rot = unreal.Rotator(float(rotation[0]), float(rotation[1]), float(rotation[2]))
    else:
        rot = unreal.Rotator(0, 0, 0)

    # Map common class names to full paths
    class_mapping = {
        # Core actors
        "StaticMeshActor": "/Script/Engine.StaticMeshActor",
        "PointLight": "/Script/Engine.PointLight",
        "SpotLight": "/Script/Engine.SpotLight",
        "DirectionalLight": "/Script/Engine.DirectionalLight",
        "RectLight": "/Script/Engine.RectLight",
        "SkyLight": "/Script/Engine.SkyLight",
        "CameraActor": "/Script/Engine.CameraActor",
        "CineCameraActor": "/Script/CinematicCamera.CineCameraActor",
        "PlayerStart": "/Script/Engine.PlayerStart",
        "TargetPoint": "/Script/Engine.TargetPoint",
        "Note": "/Script/Engine.Note",

        # Volumes
        "TriggerBox": "/Script/Engine.TriggerBox",
        "TriggerSphere": "/Script/Engine.TriggerSphere",
        "BlockingVolume": "/Script/Engine.BlockingVolume",
        "PostProcessVolume": "/Script/Engine.PostProcessVolume",
        "LightmassImportanceVolume": "/Script/Engine.LightmassImportanceVolume",

        # Basic shapes (all use StaticMeshActor + mesh)
        "Cube": "/Script/Engine.StaticMeshActor",
        "Sphere": "/Script/Engine.StaticMeshActor",
        "Cylinder": "/Script/Engine.StaticMeshActor",
        "Cone": "/Script/Engine.StaticMeshActor",
        "Plane": "/Script/Engine.StaticMeshActor",

        # Audio
        "AmbientSound": "/Script/Engine.AmbientSound",

        # Effects
        "ExponentialHeightFog": "/Script/Engine.ExponentialHeightFog",
        "AtmosphericFog": "/Script/Engine.AtmosphericFog",
        "SkyAtmosphere": "/Script/Engine.SkyAtmosphere",
        "VolumetricCloud": "/Script/Engine.VolumetricCloud",

        # Decals
        "DecalActor": "/Script/Engine.DecalActor",
    }

    class_path = class_mapping.get(actor_class, f"/Script/Engine.{actor_class}")

    try:
        actor_class_obj = unreal.load_class(None, class_path)
        if not actor_class_obj:
            return {"success": False, "error": f"Could not load class: {class_path}"}

        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class_obj, loc, rot
        )

        if not actor:
            return {"success": False, "error": "Failed to spawn actor"}

        # Set name/label
        if name:
            actor.set_actor_label(name)

        # Set scale if provided
        if scale != [1, 1, 1]:
            scale_vec = unreal.Vector(float(scale[0]), float(scale[1]), float(scale[2]))
            actor.set_actor_scale3d(scale_vec)

        # For basic shapes, try to set mesh
        if actor_class in ["Cube", "Sphere", "Cylinder", "Cone", "Plane"]:
            mesh_paths = {
                "Cube": "/Engine/BasicShapes/Cube.Cube",
                "Sphere": "/Engine/BasicShapes/Sphere.Sphere",
                "Cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
                "Cone": "/Engine/BasicShapes/Cone.Cone",
                "Plane": "/Engine/BasicShapes/Plane.Plane",
            }
            try:
                mesh_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
                if mesh_comp:
                    mesh = unreal.load_asset(mesh_paths[actor_class])
                    if mesh:
                        mesh_comp.set_static_mesh(mesh)
            except:
                pass  # Mesh setting is optional

        return {
            "success": True,
            "actor": actor.get_actor_label(),
            "location": [loc.x, loc.y, loc.z],
            "class": actor_class
        }

    except Exception as e:
        return {"success": False, "error": f"Spawn failed: {e}"}


def delete_actor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an actor by name"""
    import unreal

    actor_name = data.get("actor_name", "") or data.get("name", "")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    for actor in actors:
        if actor.get_actor_label() == actor_name:
            actor.destroy_actor()
            return {"success": True, "deleted": actor_name}
        # Also check internal name
        if actor.get_name() == actor_name:
            actor.destroy_actor()
            return {"success": True, "deleted": actor_name}

    return {"success": False, "error": f"Actor not found: {actor_name}"}


def list_actors(data: Dict[str, Any]) -> Dict[str, Any]:
    """List all actors in the level"""
    import unreal

    class_filter = data.get("class_filter", "")
    include_details = data.get("include_details", False)
    exact_match = data.get("exact_match", False)

    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    result = []
    for actor in actors:
        actor_class = actor.get_class().get_name()

        # Apply class filter if provided
        if class_filter:
            if exact_match:
                # Exact match mode
                if actor_class.lower() != class_filter.lower():
                    continue
            else:
                # Improved partial match: must start with filter or be exact
                filter_lower = class_filter.lower()
                class_lower = actor_class.lower()
                # Match if class starts with filter, or filter equals class
                if not (class_lower == filter_lower or
                        class_lower.startswith(filter_lower) or
                        filter_lower == class_lower.replace('actor', '')):
                    continue

        if include_details:
            loc = actor.get_actor_location()
            rot = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()

            result.append({
                "name": actor.get_actor_label(),
                "class": actor_class,
                "location": [loc.x, loc.y, loc.z],
                "rotation": [rot.pitch, rot.yaw, rot.roll],
                "scale": [scale.x, scale.y, scale.z]
            })
        else:
            result.append(actor.get_actor_label())

    return {
        "success": True,
        "actors": result,
        "count": len(result)
    }


def get_actor_location(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get an actor's location"""
    import unreal

    actor_name = data.get("actor_name", "") or data.get("name", "")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    actor = _find_actor_by_name(actor_name)

    if not actor:
        return {"success": False, "error": f"Actor not found: {actor_name}"}

    loc = actor.get_actor_location()
    rot = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()

    return {
        "success": True,
        "actor": actor_name,
        "location": [loc.x, loc.y, loc.z],
        "rotation": [rot.pitch, rot.yaw, rot.roll],
        "scale": [scale.x, scale.y, scale.z]
    }


def set_actor_location(data: Dict[str, Any]) -> Dict[str, Any]:
    """Set an actor's location"""
    import unreal

    actor_name = data.get("actor_name", "") or data.get("name", "")
    location = data.get("location", [])

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    if not location or len(location) < 3:
        return {"success": False, "error": "location [x, y, z] is required"}

    actor = _find_actor_by_name(actor_name)

    if not actor:
        return {"success": False, "error": f"Actor not found: {actor_name}"}

    loc = unreal.Vector(float(location[0]), float(location[1]), float(location[2]))
    actor.set_actor_location(loc, False, False)

    return {
        "success": True,
        "actor": actor_name,
        "location": [loc.x, loc.y, loc.z]
    }


def set_actor_rotation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Set an actor's rotation"""
    import unreal

    actor_name = data.get("actor_name", "") or data.get("name", "")
    rotation = data.get("rotation", [])

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    if not rotation or len(rotation) < 3:
        return {"success": False, "error": "rotation [pitch, yaw, roll] is required"}

    actor = _find_actor_by_name(actor_name)

    if not actor:
        return {"success": False, "error": f"Actor not found: {actor_name}"}

    rot = unreal.Rotator(float(rotation[0]), float(rotation[1]), float(rotation[2]))
    actor.set_actor_rotation(rot, False)

    return {
        "success": True,
        "actor": actor_name,
        "rotation": [rot.pitch, rot.yaw, rot.roll]
    }


def set_actor_scale(data: Dict[str, Any]) -> Dict[str, Any]:
    """Set an actor's scale"""
    import unreal

    actor_name = data.get("actor_name", "") or data.get("name", "")
    scale = data.get("scale", [])

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    if not scale or len(scale) < 3:
        return {"success": False, "error": "scale [x, y, z] is required"}

    actor = _find_actor_by_name(actor_name)

    if not actor:
        return {"success": False, "error": f"Actor not found: {actor_name}"}

    scale_vec = unreal.Vector(float(scale[0]), float(scale[1]), float(scale[2]))
    actor.set_actor_scale3d(scale_vec)

    return {
        "success": True,
        "actor": actor_name,
        "scale": [scale_vec.x, scale_vec.y, scale_vec.z]
    }


def modify_actor_property(data: Dict[str, Any]) -> Dict[str, Any]:
    """Modify an actor's property with automatic type conversion"""
    import unreal

    actor_name = data.get("actor_name", "") or data.get("name", "")
    property_name = data.get("property_name", "") or data.get("property", "")
    value = data.get("value")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    if not property_name:
        return {"success": False, "error": "property_name is required"}

    if value is None:
        return {"success": False, "error": "value is required"}

    actor = _find_actor_by_name(actor_name)

    if not actor:
        return {"success": False, "error": f"Actor not found: {actor_name}"}

    try:
        # Convert string values to appropriate types
        converted_value = _convert_property_value(value, property_name)

        # Try to set the property using editor property functions
        actor.set_editor_property(property_name, converted_value)

        return {
            "success": True,
            "actor": actor_name,
            "property": property_name,
            "value": str(converted_value)
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to set property: {e}"}


def _convert_property_value(value: Any, property_name: str) -> Any:
    """Convert string values to appropriate types for Unreal properties"""
    # If already correct type, return as-is
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value

    # Handle string representations
    if isinstance(value, str):
        value_lower = value.lower().strip()

        # Boolean conversion
        if value_lower in ('true', 'yes', '1', 'on'):
            return True
        if value_lower in ('false', 'no', '0', 'off'):
            return False

        # Integer conversion
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass

        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass

    return value


def _find_actor_by_name(name: str):
    """Find an actor by label or internal name"""
    import unreal

    actors = unreal.EditorLevelLibrary.get_all_level_actors()

    # Try label first (what users see in Outliner)
    for actor in actors:
        if actor.get_actor_label() == name:
            return actor

    # Try internal name
    for actor in actors:
        if actor.get_name() == name:
            return actor

    return None
