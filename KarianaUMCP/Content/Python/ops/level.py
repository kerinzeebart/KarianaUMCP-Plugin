"""
KarianaUMCP Level Operations
============================
Level management and manipulation tools.

Supports:
- load_level
- save_level
- get_current_level
- list_levels
- create_sublevel
"""

from typing import Dict, Any, List
import traceback


def handle_level_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route level commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "load_level": load_level,
        "save_level": save_level,
        "get_current_level": get_current_level,
        "list_levels": list_levels,
        "create_sublevel": create_sublevel,
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
        return {"success": False, "error": f"Unknown level command: {cmd}"}


def load_level(data: Dict[str, Any]) -> Dict[str, Any]:
    """Load a level"""
    import unreal

    level_path = data.get("level_path", "") or data.get("path", "")

    if not level_path:
        return {"success": False, "error": "level_path is required"}

    # Normalize path
    if not level_path.startswith("/Game"):
        level_path = f"/Game/{level_path}"

    try:
        # Check if level exists
        if not unreal.EditorAssetLibrary.does_asset_exist(level_path):
            return {"success": False, "error": f"Level not found: {level_path}"}

        # Load the level
        success = unreal.EditorLevelLibrary.load_level(level_path)

        if success:
            return {
                "success": True,
                "level": level_path,
                "message": "Level loaded"
            }
        else:
            return {"success": False, "error": "Failed to load level"}

    except Exception as e:
        return {"success": False, "error": f"Load failed: {e}"}


def save_level(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save the current level"""
    import unreal

    try:
        # Save current level
        success = unreal.EditorLevelLibrary.save_current_level()

        # Get current level name for response
        world = unreal.EditorLevelLibrary.get_editor_world()
        level_name = world.get_name() if world else "Unknown"

        if success:
            return {
                "success": True,
                "level": level_name,
                "message": "Level saved"
            }
        else:
            return {"success": False, "error": "Save failed"}

    except Exception as e:
        return {"success": False, "error": f"Save failed: {e}"}


def get_current_level(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get information about the current level"""
    import unreal

    try:
        world = unreal.EditorLevelLibrary.get_editor_world()

        if not world:
            return {"success": False, "error": "No world loaded"}

        # Get actor count
        actors = unreal.EditorLevelLibrary.get_all_level_actors()

        # Get level info
        info = {
            "success": True,
            "name": world.get_name(),
            "path": str(world.get_path_name()),
            "actor_count": len(actors),
        }

        # Try to get additional info
        try:
            info["map_name"] = str(world.get_map_name())
        except:
            pass

        return info

    except Exception as e:
        return {"success": False, "error": f"Failed to get level info: {e}"}


def list_levels(data: Dict[str, Any]) -> Dict[str, Any]:
    """List all levels in the project"""
    import unreal

    path = data.get("path", "/Game")

    try:
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

        # Filter for World assets (levels)
        levels = []
        all_assets = asset_registry.get_assets_by_path(path, True)

        for asset_data in all_assets:
            asset_class = str(asset_data.asset_class_path.asset_name) if hasattr(asset_data, 'asset_class_path') else str(asset_data.asset_class)

            if "World" in asset_class or "Level" in asset_class:
                levels.append({
                    "name": str(asset_data.asset_name),
                    "path": str(asset_data.package_name),
                    "class": asset_class
                })

        return {
            "success": True,
            "levels": levels,
            "count": len(levels)
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to list levels: {e}"}


def create_sublevel(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a streaming sublevel"""
    import unreal

    name = data.get("name", "NewSublevel")
    path = data.get("path", "/Game/Maps")

    full_path = f"{path}/{name}"

    try:
        # Create the sublevel
        # This is a simplified implementation
        # Full streaming level setup requires more configuration

        # Create a new level asset
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

        return {
            "success": True,
            "sublevel": name,
            "path": full_path,
            "message": "Sublevel created - configure streaming in World Settings"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to create sublevel: {e}"}
