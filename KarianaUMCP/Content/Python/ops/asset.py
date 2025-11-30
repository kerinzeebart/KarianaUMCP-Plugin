"""
KarianaUMCP Asset Operations
============================
Asset management and manipulation tools.

Supports:
- import_asset
- list_assets
- create_material
- get_asset_info
- save_asset
- delete_asset
- duplicate_asset
"""

from typing import Dict, Any, List
import traceback


def handle_asset_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route asset commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "import_asset": import_asset,
        "list_assets": list_assets,
        "create_material": create_material,
        "get_asset_info": get_asset_info,
        "save_asset": save_asset,
        "delete_asset": delete_asset,
        "duplicate_asset": duplicate_asset,
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
        return {"success": False, "error": f"Unknown asset command: {cmd}"}


def import_asset(data: Dict[str, Any]) -> Dict[str, Any]:
    """Import an asset from file"""
    import unreal
    import os

    source_path = data.get("source_path", "")
    destination_path = data.get("destination_path", "/Game/Imported")
    asset_name = data.get("asset_name", "")

    if not source_path:
        return {"success": False, "error": "source_path is required"}

    if not os.path.exists(source_path):
        return {"success": False, "error": f"Source file not found: {source_path}"}

    # Auto-detect asset name from filename
    if not asset_name:
        asset_name = os.path.splitext(os.path.basename(source_path))[0]

    try:
        # Create import task
        task = unreal.AssetImportTask()
        task.set_editor_property('automated', True)
        task.set_editor_property('destination_path', destination_path)
        task.set_editor_property('destination_name', asset_name)
        task.set_editor_property('filename', source_path)
        task.set_editor_property('replace_existing', True)
        task.set_editor_property('save', True)

        # Execute import
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        asset_tools.import_asset_tasks([task])

        imported_path = f"{destination_path}/{asset_name}"

        # Verify import
        imported_asset = unreal.load_asset(imported_path)
        if imported_asset:
            return {
                "success": True,
                "asset": asset_name,
                "path": imported_path,
                "source": source_path
            }
        else:
            return {
                "success": False,
                "error": "Import completed but asset not found"
            }

    except Exception as e:
        return {"success": False, "error": f"Import failed: {e}"}


def list_assets(data: Dict[str, Any]) -> Dict[str, Any]:
    """List assets in a directory"""
    import unreal

    path = data.get("path", "/Game")
    recursive = data.get("recursive", True)
    class_filter = data.get("class_filter", "")
    limit = data.get("limit", 100)

    # Normalize path
    if not path.startswith("/Game"):
        path = f"/Game/{path}"

    try:
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

        # Get assets
        assets = asset_registry.get_assets_by_path(path, recursive)

        result = []
        for asset_data in assets:
            if len(result) >= limit:
                break

            asset_class = str(asset_data.asset_class_path.asset_name) if hasattr(asset_data, 'asset_class_path') else str(asset_data.asset_class)

            # Apply class filter
            if class_filter and class_filter.lower() not in asset_class.lower():
                continue

            result.append({
                "name": str(asset_data.asset_name),
                "path": str(asset_data.package_name),
                "class": asset_class
            })

        return {
            "success": True,
            "assets": result,
            "count": len(result),
            "path": path
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to list assets: {e}"}


def create_material(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new material"""
    import unreal

    name = data.get("name", "NewMaterial")
    path = data.get("path", "/Game/Materials")
    base_color = data.get("base_color", [1, 1, 1, 1])
    metallic = data.get("metallic", 0.0)
    roughness = data.get("roughness", 0.5)

    full_path = f"{path}/{name}"

    try:
        # Create material factory
        factory = unreal.MaterialFactoryNew()

        # Create the material
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        material = asset_tools.create_asset(name, path, unreal.Material, factory)

        if not material:
            return {"success": False, "error": "Failed to create material"}

        # Set material properties (basic setup)
        # Note: Full material setup requires node graph manipulation

        # Save the material
        unreal.EditorAssetLibrary.save_asset(full_path)

        return {
            "success": True,
            "material": name,
            "path": full_path,
            "message": "Material created - open in editor for advanced setup"
        }

    except Exception as e:
        return {"success": False, "error": f"Material creation failed: {e}"}


def get_asset_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get information about an asset"""
    import unreal

    asset_path = data.get("asset_path", "") or data.get("path", "")

    if not asset_path:
        return {"success": False, "error": "asset_path is required"}

    # Normalize path
    if not asset_path.startswith("/Game") and not asset_path.startswith("/Engine"):
        asset_path = f"/Game/{asset_path}"

    try:
        # Load the asset
        asset = unreal.load_asset(asset_path)

        if not asset:
            return {"success": False, "error": f"Asset not found: {asset_path}"}

        info = {
            "success": True,
            "path": asset_path,
            "name": asset.get_name(),
            "class": asset.get_class().get_name(),
        }

        # Try to get additional info based on asset type
        asset_class = asset.get_class().get_name()

        if "Texture" in asset_class:
            try:
                info["size"] = {
                    "width": asset.get_editor_property("source_width"),
                    "height": asset.get_editor_property("source_height")
                }
            except:
                pass

        elif "StaticMesh" in asset_class:
            try:
                info["num_lods"] = asset.get_num_lods()
            except:
                pass

        return info

    except Exception as e:
        return {"success": False, "error": f"Failed to get asset info: {e}"}


def save_asset(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save an asset"""
    import unreal

    asset_path = data.get("asset_path", "") or data.get("path", "")

    if not asset_path:
        return {"success": False, "error": "asset_path is required"}

    # Normalize path
    if not asset_path.startswith("/Game"):
        asset_path = f"/Game/{asset_path}"

    try:
        success = unreal.EditorAssetLibrary.save_asset(asset_path)

        if success:
            return {
                "success": True,
                "asset": asset_path,
                "message": "Asset saved"
            }
        else:
            return {"success": False, "error": "Save failed"}

    except Exception as e:
        return {"success": False, "error": f"Save failed: {e}"}


def delete_asset(data: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an asset"""
    import unreal

    asset_path = data.get("asset_path", "") or data.get("path", "")

    if not asset_path:
        return {"success": False, "error": "asset_path is required"}

    # Normalize path
    if not asset_path.startswith("/Game"):
        asset_path = f"/Game/{asset_path}"

    try:
        # Check if asset exists
        if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            return {"success": False, "error": f"Asset not found: {asset_path}"}

        # Delete the asset
        success = unreal.EditorAssetLibrary.delete_asset(asset_path)

        if success:
            return {
                "success": True,
                "deleted": asset_path
            }
        else:
            return {"success": False, "error": "Delete failed"}

    except Exception as e:
        return {"success": False, "error": f"Delete failed: {e}"}


def duplicate_asset(data: Dict[str, Any]) -> Dict[str, Any]:
    """Duplicate an asset"""
    import unreal

    source_path = data.get("source_path", "")
    destination_path = data.get("destination_path", "")

    if not source_path:
        return {"success": False, "error": "source_path is required"}

    if not destination_path:
        return {"success": False, "error": "destination_path is required"}

    # Normalize paths
    if not source_path.startswith("/Game"):
        source_path = f"/Game/{source_path}"
    if not destination_path.startswith("/Game"):
        destination_path = f"/Game/{destination_path}"

    try:
        # Duplicate
        success = unreal.EditorAssetLibrary.duplicate_asset(source_path, destination_path)

        if success:
            return {
                "success": True,
                "source": source_path,
                "destination": destination_path
            }
        else:
            return {"success": False, "error": "Duplicate failed"}

    except Exception as e:
        return {"success": False, "error": f"Duplicate failed: {e}"}
