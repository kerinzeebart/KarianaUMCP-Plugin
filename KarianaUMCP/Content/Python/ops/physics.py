"""
KarianaUMCP Physics Operations
==============================
Physics simulation tools.

Supports:
- enable_physics_on_actor
- disable_physics_on_actor
- get_actor_physics_status
"""

from typing import Dict, Any, List, Optional
import traceback


def handle_physics_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route physics commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "enable_physics_on_actor": enable_physics_on_actor,
        "disable_physics_on_actor": disable_physics_on_actor,
        "get_actor_physics_status": get_actor_physics_status,
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
        return {"success": False, "error": f"Unknown physics command: {cmd}"}


def _find_actor_by_name(actor_name: str):
    """Helper to find actor by label"""
    import unreal
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in actors:
        if actor.get_actor_label() == actor_name:
            return actor
    return None


def _get_primitive_component(actor):
    """Get the primitive component from an actor"""
    import unreal

    # Try to get StaticMeshComponent first
    if hasattr(actor, 'static_mesh_component'):
        return actor.static_mesh_component

    # Try to get component by class
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component:
        return component

    # Try SkeletalMeshComponent
    component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    if component:
        return component

    # Try any PrimitiveComponent
    component = actor.get_component_by_class(unreal.PrimitiveComponent)
    return component


def enable_physics_on_actor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Enable physics simulation on an actor.

    Args:
        actor_name: Name of the actor
        enable_gravity: Enable gravity (default True)
        linear_damping: Linear damping value (default 0.01)
        angular_damping: Angular damping value (default 0.0)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    enable_gravity = data.get("enable_gravity", True)
    linear_damping = data.get("linear_damping", 0.01)
    angular_damping = data.get("angular_damping", 0.0)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        component = _get_primitive_component(actor)
        if not component:
            return {"success": False, "error": f"No primitive component found on actor: {actor_name}"}

        # Enable physics simulation
        component.set_simulate_physics(True)
        component.set_enable_gravity(enable_gravity)
        component.set_linear_damping(linear_damping)
        component.set_angular_damping(angular_damping)

        return {
            "success": True,
            "actor_name": actor_name,
            "component": component.get_name(),
            "physics_enabled": True,
            "gravity_enabled": enable_gravity,
            "linear_damping": linear_damping,
            "angular_damping": angular_damping,
            "message": f"Physics enabled on {actor_name}"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to enable physics: {e}"}


def disable_physics_on_actor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Disable physics simulation on an actor.

    Args:
        actor_name: Name of the actor
    """
    import unreal

    actor_name = data.get("actor_name", "")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        component = _get_primitive_component(actor)
        if not component:
            return {"success": False, "error": f"No primitive component found on actor: {actor_name}"}

        # Disable physics simulation
        component.set_simulate_physics(False)

        return {
            "success": True,
            "actor_name": actor_name,
            "component": component.get_name(),
            "physics_enabled": False,
            "message": f"Physics disabled on {actor_name}"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to disable physics: {e}"}


def get_actor_physics_status(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get the physics status of an actor.

    Args:
        actor_name: Name of the actor
    """
    import unreal

    actor_name = data.get("actor_name", "")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        component = _get_primitive_component(actor)
        if not component:
            return {
                "success": True,
                "actor_name": actor_name,
                "has_physics_component": False,
                "message": "No physics-capable component found"
            }

        # Get physics properties
        physics_enabled = component.is_simulating_physics()
        gravity_enabled = component.is_gravity_enabled()

        result = {
            "success": True,
            "actor_name": actor_name,
            "component_name": component.get_name(),
            "component_class": component.get_class().get_name(),
            "has_physics_component": True,
            "physics_enabled": physics_enabled,
            "gravity_enabled": gravity_enabled
        }

        # Try to get additional physics properties
        try:
            result["linear_damping"] = component.get_linear_damping()
            result["angular_damping"] = component.get_angular_damping()
            result["mass"] = component.get_mass()
        except Exception:
            pass

        # Get velocity if physics is enabled
        if physics_enabled:
            try:
                vel = component.get_physics_linear_velocity()
                ang_vel = component.get_physics_angular_velocity_in_degrees()
                result["linear_velocity"] = [vel.x, vel.y, vel.z]
                result["angular_velocity"] = [ang_vel.x, ang_vel.y, ang_vel.z]
            except Exception:
                pass

        return result

    except Exception as e:
        return {"success": False, "error": f"Failed to get physics status: {e}"}
