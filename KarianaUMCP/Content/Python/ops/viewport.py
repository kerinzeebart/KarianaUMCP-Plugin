"""
KarianaUMCP Viewport Operations
===============================
Viewport and camera control tools.

Supports:
- focus_on_actor
- set_render_mode
- look_at_target
- set_view_mode
- fit_actors
- get_viewport_bounds
- set_camera
"""

from typing import Dict, Any, List, Optional
import traceback
import math


def handle_viewport_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route viewport commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "focus_on_actor": focus_on_actor,
        "set_render_mode": set_render_mode,
        "look_at_target": look_at_target,
        "set_view_mode": set_view_mode,
        "fit_actors": fit_actors,
        "get_viewport_bounds": get_viewport_bounds,
        "set_camera": set_camera,
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
        return {"success": False, "error": f"Unknown viewport command: {cmd}"}


def _find_actor_by_name(actor_name: str):
    """Helper to find actor by label"""
    import unreal
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in actors:
        if actor.get_actor_label() == actor_name:
            return actor
    return None


def focus_on_actor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Focus viewport on a specific actor.

    Args:
        actor_name: Name of the actor to focus on
        preserve_rotation: Whether to keep current camera angles (default False)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    preserve_rotation = data.get("preserve_rotation", False)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    try:
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        # Select the actor
        editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        editor_actor_subsystem.set_selected_level_actors([actor])

        # Get editor subsystem
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

        # Get actor's location and bounds
        actor_location = actor.get_actor_location()
        actor_bounds = actor.get_actor_bounds(only_colliding_components=False)
        bounds_extent = actor_bounds[1]

        # Calculate camera distance
        max_extent = max(bounds_extent.x, bounds_extent.y, bounds_extent.z)
        camera_distance = max_extent * 3 if max_extent > 0 else 500

        if preserve_rotation:
            # Get current camera rotation
            current_location, current_rotation = editor_subsystem.get_level_viewport_camera_info()

            # Check if we're in a top-down view
            if abs(current_rotation.pitch + 90) < 5:
                # Keep top-down view
                camera_location = unreal.Vector(
                    actor_location.x,
                    actor_location.y,
                    actor_location.z + camera_distance
                )
                camera_rotation = current_rotation
            else:
                # Calculate offset based on current rotation
                forward_vector = current_rotation.get_forward_vector()
                camera_location = actor_location - (forward_vector * camera_distance)
                camera_rotation = current_rotation
        else:
            # Set camera to look at the actor from a nice angle
            camera_offset = unreal.Vector(-camera_distance, -camera_distance * 0.5, camera_distance * 0.5)
            camera_location = actor_location + camera_offset

            # Calculate rotation to look at actor
            camera_rotation = unreal.MathLibrary.find_look_at_rotation(camera_location, actor_location)

        # Set the viewport camera
        editor_subsystem.set_level_viewport_camera_info(camera_location, camera_rotation)

        return {
            "success": True,
            "actor": actor_name,
            "location": {
                "x": float(actor_location.x),
                "y": float(actor_location.y),
                "z": float(actor_location.z)
            },
            "message": f"Focused viewport on: {actor_name}"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to focus on actor: {e}"}


def set_render_mode(data: Dict[str, Any]) -> Dict[str, Any]:
    """Change viewport rendering mode.

    Args:
        mode: Rendering mode (lit, unlit, wireframe, detail_lighting,
              lighting_only, light_complexity, shader_complexity)
    """
    import unreal

    mode = data.get("mode", "lit").lower()

    mode_commands = {
        "lit": ["ShowFlag.Wireframe 0", "ShowFlag.Materials 1", "ShowFlag.Lighting 1", "viewmode lit"],
        "unlit": ["viewmode unlit"],
        "wireframe": ["ShowFlag.Wireframe 1", "ShowFlag.Materials 0", "ShowFlag.Lighting 0"],
        "detail_lighting": ["viewmode lit_detaillighting"],
        "lighting_only": ["viewmode lightingonly"],
        "light_complexity": ["viewmode lightcomplexity"],
        "shader_complexity": ["viewmode shadercomplexity"],
    }

    if mode not in mode_commands:
        valid_modes = ", ".join(mode_commands.keys())
        return {"success": False, "error": f"Invalid render mode: {mode}. Valid modes: {valid_modes}"}

    try:
        # Get editor world for console commands
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor_subsystem.get_editor_world()

        # Execute console commands for the mode
        for cmd in mode_commands[mode]:
            unreal.SystemLibrary.execute_console_command(world, cmd, None)

        return {
            "success": True,
            "mode": mode,
            "message": f"Viewport render mode set to {mode}"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to set render mode: {e}"}


def look_at_target(data: Dict[str, Any]) -> Dict[str, Any]:
    """Point viewport camera to look at specific coordinates or actor.

    Args:
        target: [X, Y, Z] target location (optional if actor_name provided)
        actor_name: Name of actor to look at (optional if target provided)
        distance: Distance from target (default 1000)
        pitch: Camera pitch angle (default -30)
        height: Camera height offset (default 500)
    """
    import unreal

    target = data.get("target")
    actor_name = data.get("actor_name")
    distance = float(data.get("distance", 1000))
    pitch = float(data.get("pitch", -30))
    height = float(data.get("height", 500))

    try:
        # Get target location
        if actor_name:
            actor = _find_actor_by_name(actor_name)
            if not actor:
                return {"success": False, "error": f"Actor not found: {actor_name}"}
            target_location = actor.get_actor_location()
        elif target and len(target) >= 3:
            target_location = unreal.Vector(float(target[0]), float(target[1]), float(target[2]))
        else:
            return {"success": False, "error": "Must provide either target coordinates or actor_name"}

        # Calculate camera position
        angle = -45 * math.pi / 180  # -45 degrees in radians

        camera_x = target_location.x + distance * math.cos(angle)
        camera_y = target_location.y + distance * math.sin(angle)
        camera_z = target_location.z + height

        camera_location = unreal.Vector(camera_x, camera_y, camera_z)

        # Calculate yaw to look at target
        dx = target_location.x - camera_x
        dy = target_location.y - camera_y

        # Calculate angle and convert to Unreal's coordinate system
        angle_rad = math.atan2(dy, dx)
        yaw = -(angle_rad * 180 / math.pi)

        # Set camera rotation
        camera_rotation = unreal.Rotator()
        camera_rotation.roll = 0.0
        camera_rotation.pitch = float(pitch)
        camera_rotation.yaw = float(yaw)

        # Apply to viewport
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        editor_subsystem.set_level_viewport_camera_info(camera_location, camera_rotation)

        return {
            "success": True,
            "camera_location": [camera_location.x, camera_location.y, camera_location.z],
            "camera_rotation": [camera_rotation.roll, camera_rotation.pitch, camera_rotation.yaw],
            "target_location": [target_location.x, target_location.y, target_location.z],
            "message": "Camera positioned to look at target"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to look at target: {e}"}


def set_view_mode(data: Dict[str, Any]) -> Dict[str, Any]:
    """Position camera for standard views (top, front, side, etc.).

    Args:
        mode: View mode (perspective, top, bottom, left, right, front, back)
    """
    import unreal

    mode = data.get("mode", "perspective").lower()

    valid_modes = ["perspective", "top", "bottom", "left", "right", "front", "back"]
    if mode not in valid_modes:
        return {"success": False, "error": f"Invalid mode: {mode}. Valid modes: {', '.join(valid_modes)}"}

    try:
        # Get editor subsystem
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

        # Get current location to maintain position
        current_location, current_rotation = editor_subsystem.get_level_viewport_camera_info()

        # Create rotation for each mode
        rotation = unreal.Rotator()
        if mode == "top":
            rotation.pitch = -90.0
            rotation.yaw = 0.0
            rotation.roll = 0.0
        elif mode == "bottom":
            rotation.pitch = 90.0
            rotation.yaw = 0.0
            rotation.roll = 0.0
        elif mode == "front":
            rotation.pitch = 0.0
            rotation.yaw = 0.0
            rotation.roll = 0.0
        elif mode == "back":
            rotation.pitch = 0.0
            rotation.yaw = 180.0
            rotation.roll = 0.0
        elif mode == "left":
            rotation.pitch = 0.0
            rotation.yaw = -90.0
            rotation.roll = 0.0
        elif mode == "right":
            rotation.pitch = 0.0
            rotation.yaw = 90.0
            rotation.roll = 0.0
        else:  # perspective
            rotation.pitch = -30.0
            rotation.yaw = 45.0
            rotation.roll = 0.0

        # Check if any actors are selected for centering
        editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        selected_actors = editor_actor_subsystem.get_selected_level_actors()

        if selected_actors:
            # Center on selected actors
            bounds_origin = unreal.Vector(0, 0, 0)
            bounds_extent = unreal.Vector(0, 0, 0)

            # Calculate combined bounds
            for i, actor in enumerate(selected_actors):
                actor_origin, actor_extent = actor.get_actor_bounds(False)
                if i == 0:
                    bounds_origin = actor_origin
                    bounds_extent = actor_extent
                else:
                    # Expand bounds to include this actor
                    min_point = unreal.Vector(
                        min(bounds_origin.x - bounds_extent.x, actor_origin.x - actor_extent.x),
                        min(bounds_origin.y - bounds_extent.y, actor_origin.y - actor_extent.y),
                        min(bounds_origin.z - bounds_extent.z, actor_origin.z - actor_extent.z)
                    )
                    max_point = unreal.Vector(
                        max(bounds_origin.x + bounds_extent.x, actor_origin.x + actor_extent.x),
                        max(bounds_origin.y + bounds_extent.y, actor_origin.y + actor_extent.y),
                        max(bounds_origin.z + bounds_extent.z, actor_origin.z + actor_extent.z)
                    )
                    bounds_origin = (min_point + max_point) * 0.5
                    bounds_extent = (max_point - min_point) * 0.5

            # Calculate camera distance based on bounds
            max_extent = max(bounds_extent.x, bounds_extent.y, bounds_extent.z)
            distance = max_extent * 3 if max_extent > 0 else 1000

            # Position camera based on mode
            if mode == "top":
                location = unreal.Vector(bounds_origin.x, bounds_origin.y, bounds_origin.z + distance)
            elif mode == "bottom":
                location = unreal.Vector(bounds_origin.x, bounds_origin.y, bounds_origin.z - distance)
            elif mode == "front":
                location = unreal.Vector(bounds_origin.x - distance, bounds_origin.y, bounds_origin.z)
            elif mode == "back":
                location = unreal.Vector(bounds_origin.x + distance, bounds_origin.y, bounds_origin.z)
            elif mode == "left":
                location = unreal.Vector(bounds_origin.x, bounds_origin.y - distance, bounds_origin.z)
            elif mode == "right":
                location = unreal.Vector(bounds_origin.x, bounds_origin.y + distance, bounds_origin.z)
            else:  # perspective
                location = unreal.Vector(
                    bounds_origin.x - distance * 0.7,
                    bounds_origin.y - distance * 0.7,
                    bounds_origin.z + distance * 0.5
                )
        else:
            # No selection, maintain current location
            location = current_location

        # Apply the camera transform
        editor_subsystem.set_level_viewport_camera_info(location, rotation)

        return {
            "success": True,
            "mode": mode,
            "location": [location.x, location.y, location.z],
            "rotation": [rotation.roll, rotation.pitch, rotation.yaw],
            "message": f"Camera set to {mode} view"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to set view mode: {e}"}


def fit_actors(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fit actors in viewport by adjusting camera position.

    Args:
        actors: List of specific actor names to fit (optional)
        filter: Pattern to filter actor names (optional)
        padding: Padding percentage around actors (default 20)
    """
    import unreal

    actors_list = data.get("actors", [])
    filter_pattern = data.get("filter", "")
    padding = data.get("padding", 20)

    if not actors_list and not filter_pattern:
        return {"success": False, "error": "Must provide either actors list or filter pattern"}

    try:
        # Get all actors to check
        editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        all_actors = editor_actor_subsystem.get_all_level_actors()

        # Filter actors based on provided criteria
        actors_to_fit = []

        if actors_list:
            # Specific actors requested
            for actor in all_actors:
                if actor and hasattr(actor, "get_actor_label"):
                    if actor.get_actor_label() in actors_list:
                        actors_to_fit.append(actor)
        elif filter_pattern:
            # Filter pattern provided
            filter_lower = filter_pattern.lower()
            for actor in all_actors:
                if actor and hasattr(actor, "get_actor_label"):
                    if filter_lower in actor.get_actor_label().lower():
                        actors_to_fit.append(actor)

        if not actors_to_fit:
            return {"success": False, "error": "No actors found matching criteria"}

        # Calculate combined bounds of all actors
        combined_min = None
        combined_max = None

        for actor in actors_to_fit:
            origin, extent = actor.get_actor_bounds(False)

            actor_min = unreal.Vector(
                origin.x - extent.x,
                origin.y - extent.y,
                origin.z - extent.z
            )
            actor_max = unreal.Vector(
                origin.x + extent.x,
                origin.y + extent.y,
                origin.z + extent.z
            )

            if combined_min is None:
                combined_min = actor_min
                combined_max = actor_max
            else:
                combined_min = unreal.Vector(
                    min(combined_min.x, actor_min.x),
                    min(combined_min.y, actor_min.y),
                    min(combined_min.z, actor_min.z)
                )
                combined_max = unreal.Vector(
                    max(combined_max.x, actor_max.x),
                    max(combined_max.y, actor_max.y),
                    max(combined_max.z, actor_max.z)
                )

        # Calculate center and size
        bounds_center = (combined_min + combined_max) * 0.5
        bounds_size = combined_max - combined_min

        # Apply padding
        padding_factor = 1.0 + (padding / 100.0)

        # Calculate required camera distance
        max_dimension = max(bounds_size.x, bounds_size.y, bounds_size.z)
        camera_distance = max_dimension * padding_factor

        # Get current camera rotation to maintain view angle
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        current_location, current_rotation = editor_subsystem.get_level_viewport_camera_info()

        # Position camera to fit all actors
        # Use current rotation to determine camera offset direction
        forward = current_rotation.get_forward_vector()
        camera_location = bounds_center - forward * camera_distance

        # Apply the camera position
        editor_subsystem.set_level_viewport_camera_info(camera_location, current_rotation)

        # Also select the actors for clarity
        editor_actor_subsystem.set_selected_level_actors(actors_to_fit)

        return {
            "success": True,
            "fitted_actors": len(actors_to_fit),
            "actor_names": [a.get_actor_label() for a in actors_to_fit],
            "bounds_center": [bounds_center.x, bounds_center.y, bounds_center.z],
            "bounds_size": [bounds_size.x, bounds_size.y, bounds_size.z],
            "camera_location": [camera_location.x, camera_location.y, camera_location.z],
            "message": f"Fitted {len(actors_to_fit)} actors in viewport"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to fit actors in viewport: {e}"}


def get_viewport_bounds(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get current viewport boundaries and visible area."""
    import unreal

    try:
        # Get viewport camera info
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        camera_location, camera_rotation = editor_subsystem.get_level_viewport_camera_info()

        # Get FOV (default to 90 if not available)
        fov = 90.0

        # Estimate view distance (simplified)
        view_distance = 5000.0

        # Calculate rough bounds based on camera position and FOV
        half_fov_rad = math.radians(fov / 2)
        extent_at_distance = view_distance * math.tan(half_fov_rad)

        # Calculate view direction
        forward = camera_rotation.get_forward_vector()

        # Calculate center point
        center = camera_location + forward * view_distance

        min_x = center.x - extent_at_distance
        max_x = center.x + extent_at_distance
        min_y = center.y - extent_at_distance
        max_y = center.y + extent_at_distance
        min_z = center.z - extent_at_distance
        max_z = center.z + extent_at_distance

        return {
            "success": True,
            "camera": {
                "location": [camera_location.x, camera_location.y, camera_location.z],
                "rotation": [camera_rotation.roll, camera_rotation.pitch, camera_rotation.yaw]
            },
            "bounds": {
                "min": [min_x, min_y, min_z],
                "max": [max_x, max_y, max_z]
            },
            "view_distance": view_distance,
            "fov": fov,
            "message": "Viewport bounds calculated (estimated)"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to get viewport bounds: {e}"}


def set_camera(data: Dict[str, Any]) -> Dict[str, Any]:
    """Set viewport camera position and rotation.

    Args:
        location: [X, Y, Z] camera location (optional if focus_actor provided)
        rotation: [Roll, Pitch, Yaw] camera rotation (optional)
        focus_actor: Name of actor to focus on (optional)
        distance: Distance from focus actor (default 500)
    """
    import unreal

    location = data.get("location")
    rotation = data.get("rotation")
    focus_actor = data.get("focus_actor")
    distance = data.get("distance", 500)

    try:
        editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

        if focus_actor:
            # Find and focus on specific actor
            target_actor = _find_actor_by_name(focus_actor)

            if not target_actor:
                return {"success": False, "error": f"Actor not found: {focus_actor}"}

            # Get actor location and bounds
            actor_location = target_actor.get_actor_location()

            # Calculate camera position
            camera_offset = unreal.Vector(
                -distance * 0.7,  # Back
                0,                # Side
                distance * 0.7   # Up
            )
            camera_location = actor_location + camera_offset

            # Calculate rotation to look at actor
            direction = actor_location - camera_location
            camera_rotation = direction.rotation()

            # Set viewport camera
            editor_subsystem.set_level_viewport_camera_info(camera_location, camera_rotation)

            return {
                "success": True,
                "location": {
                    "x": float(camera_location.x),
                    "y": float(camera_location.y),
                    "z": float(camera_location.z)
                },
                "rotation": {
                    "pitch": float(camera_rotation.pitch),
                    "yaw": float(camera_rotation.yaw),
                    "roll": float(camera_rotation.roll)
                },
                "focus_actor": focus_actor,
                "message": f"Camera focused on {focus_actor}"
            }
        else:
            # Manual camera positioning
            if not location or len(location) < 3:
                return {"success": False, "error": "location [X, Y, Z] required when not focusing on an actor"}

            camera_location = unreal.Vector(float(location[0]), float(location[1]), float(location[2]))

            if rotation and len(rotation) >= 3:
                camera_rotation = unreal.Rotator()
                camera_rotation.roll = float(rotation[0])
                camera_rotation.pitch = float(rotation[1])
                camera_rotation.yaw = float(rotation[2])
            else:
                # Default rotation looking forward and slightly down
                camera_rotation = unreal.Rotator()
                camera_rotation.pitch = -30.0
                camera_rotation.yaw = 0.0
                camera_rotation.roll = 0.0

            editor_subsystem.set_level_viewport_camera_info(camera_location, camera_rotation)

            return {
                "success": True,
                "location": {
                    "x": float(camera_location.x),
                    "y": float(camera_location.y),
                    "z": float(camera_location.z)
                },
                "rotation": {
                    "pitch": float(camera_rotation.pitch),
                    "yaw": float(camera_rotation.yaw),
                    "roll": float(camera_rotation.roll)
                },
                "message": "Viewport camera updated"
            }

    except Exception as e:
        return {"success": False, "error": f"Failed to set camera: {e}"}
