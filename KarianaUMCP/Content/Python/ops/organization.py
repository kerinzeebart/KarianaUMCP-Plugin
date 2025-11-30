"""
KarianaUMCP Organization Operations
===================================
Asset and World Outliner organization tools.

Supports:
- create_folder_structure
- organize_assets_by_type
- organize_world_outliner
- tag_assets
- search_assets_by_tag
- generate_organization_report
"""

from typing import Dict, Any, List, Optional
import traceback


def handle_organization_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route organization commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "create_folder_structure": create_folder_structure,
        "organize_assets_by_type": organize_assets_by_type,
        "organize_world_outliner": organize_world_outliner,
        "tag_assets": tag_assets,
        "search_assets_by_tag": search_assets_by_tag,
        "generate_organization_report": generate_organization_report,
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
        return {"success": False, "error": f"Unknown organization command: {cmd}"}


def create_folder_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a folder structure in the Content Browser.

    Args:
        base_path: Base path for folder creation (default: "/Game")
        folder_structure: Dict or list defining folder hierarchy
    """
    import unreal

    base_path = data.get("base_path", "/Game")
    folder_structure = data.get("folder_structure")

    created_folders = []
    failed_folders = []

    try:
        # Default folder structure if none provided
        if folder_structure is None:
            folder_structure = {
                "Blueprints": ["Characters", "Weapons", "Items"],
                "Materials": [],
                "Meshes": ["Static", "Skeletal"],
                "Textures": [],
                "Audio": ["Music", "SFX"],
                "Input": ["Actions", "Contexts"],
                "UI": ["Widgets", "Textures"]
            }

        # Convert list to dict if needed
        if isinstance(folder_structure, list):
            folder_structure = {folder: [] for folder in folder_structure}

        # Create base path if it doesn't exist
        if not unreal.EditorAssetLibrary.does_directory_exist(base_path):
            unreal.EditorAssetLibrary.make_directory(base_path)
            created_folders.append(base_path)

        # Create folder structure
        for parent_folder, subfolders in folder_structure.items():
            parent_path = f"{base_path}/{parent_folder}"

            # Create parent folder
            if not unreal.EditorAssetLibrary.does_directory_exist(parent_path):
                success = unreal.EditorAssetLibrary.make_directory(parent_path)
                if success:
                    created_folders.append(parent_path)
                else:
                    failed_folders.append(parent_path)

            # Create subfolders
            if isinstance(subfolders, list):
                for subfolder in subfolders:
                    subfolder_path = f"{parent_path}/{subfolder}"
                    if not unreal.EditorAssetLibrary.does_directory_exist(subfolder_path):
                        success = unreal.EditorAssetLibrary.make_directory(subfolder_path)
                        if success:
                            created_folders.append(subfolder_path)
                        else:
                            failed_folders.append(subfolder_path)

        return {
            "success": True,
            "message": f"Created {len(created_folders)} folders",
            "created_folders": created_folders,
            "failed_folders": failed_folders,
            "total_created": len(created_folders),
            "total_failed": len(failed_folders)
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to create folder structure: {e}"}


def organize_assets_by_type(data: Dict[str, Any]) -> Dict[str, Any]:
    """Organize assets from source folder into target folders by type.

    Args:
        source_folder: Folder to scan for assets
        target_base: Base path for organized folders (optional)
        organization_rules: Custom rules for organization (optional)
        dry_run: If True, don't move assets, just report (optional)
    """
    import unreal

    source_folder = data.get("source_folder")
    target_base = data.get("target_base")
    organization_rules = data.get("organization_rules")
    dry_run = data.get("dry_run", False)

    if not source_folder:
        return {"success": False, "error": "source_folder is required"}

    try:
        # Default target base
        if target_base is None:
            target_base = f"{source_folder}_Organized"

        # Default organization rules
        if organization_rules is None:
            organization_rules = {
                "Blueprint": f"{target_base}/Blueprints",
                "InputAction": f"{target_base}/Input/Actions",
                "InputMappingContext": f"{target_base}/Input/Contexts",
                "Material": f"{target_base}/Materials",
                "MaterialInstance": f"{target_base}/Materials/Instances",
                "StaticMesh": f"{target_base}/Meshes/Static",
                "SkeletalMesh": f"{target_base}/Meshes/Skeletal",
                "Texture2D": f"{target_base}/Textures",
                "SoundWave": f"{target_base}/Audio/SFX",
                "AnimSequence": f"{target_base}/Animations",
                "WidgetBlueprint": f"{target_base}/UI/Widgets",
            }

        # Create necessary folders
        for folder_path in set(organization_rules.values()):
            if not unreal.EditorAssetLibrary.does_directory_exist(folder_path):
                unreal.EditorAssetLibrary.make_directory(folder_path)

        # Get all assets in source folder
        assets = unreal.EditorAssetLibrary.list_assets(source_folder, recursive=True)

        moved_assets = []
        skipped_assets = []
        failed_assets = []

        for asset_path in assets:
            asset = unreal.load_asset(asset_path)
            if not asset:
                continue

            asset_name = asset.get_name()
            asset_class = asset.get_class().get_name()

            # Find target folder for this asset type
            target_folder = organization_rules.get(asset_class)
            if not target_folder:
                skipped_assets.append({
                    "name": asset_name,
                    "class": asset_class,
                    "reason": "No rule for this asset type"
                })
                continue

            # Build new path
            new_path = f"{target_folder}/{asset_name}"

            # Skip if already in correct location
            if asset_path.startswith(target_folder):
                skipped_assets.append({
                    "name": asset_name,
                    "class": asset_class,
                    "reason": "Already in correct location"
                })
                continue

            # Move asset (or simulate if dry run)
            if dry_run:
                moved_assets.append({
                    "name": asset_name,
                    "class": asset_class,
                    "from": asset_path,
                    "to": new_path,
                    "dry_run": True
                })
            else:
                success = unreal.EditorAssetLibrary.rename_asset(asset_path, new_path)
                if success:
                    moved_assets.append({
                        "name": asset_name,
                        "class": asset_class,
                        "from": asset_path,
                        "to": new_path,
                        "moved": True
                    })
                else:
                    failed_assets.append({
                        "name": asset_name,
                        "class": asset_class,
                        "path": asset_path,
                        "target": new_path
                    })

        return {
            "success": True,
            "dry_run": dry_run,
            "source_folder": source_folder,
            "target_base": target_base,
            "total_assets_scanned": len(assets),
            "moved_count": len(moved_assets),
            "skipped_count": len(skipped_assets),
            "failed_count": len(failed_assets),
            "moved_assets": moved_assets[:20],
            "skipped_assets": skipped_assets[:10],
            "failed_assets": failed_assets
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to organize assets: {e}"}


def organize_world_outliner(data: Dict[str, Any]) -> Dict[str, Any]:
    """Organize actors in the World Outliner into folder hierarchy.

    Args:
        organization_rules: Dictionary mapping actor classes to folder paths (optional)
        target_actors: List of specific actor names to organize (optional)
    """
    import unreal

    organization_rules = data.get("organization_rules")
    target_actors = data.get("target_actors")

    try:
        # Default organization rules
        if organization_rules is None:
            organization_rules = {
                # Lighting
                "DirectionalLight": "/Environment/Lighting/Directional",
                "PointLight": "/Environment/Lighting/Point",
                "SpotLight": "/Environment/Lighting/Spot",
                "SkyLight": "/Environment/Lighting/Sky",
                "RectLight": "/Environment/Lighting/Rect",

                # Environment
                "Landscape": "/Environment/Terrain",
                "StaticMeshActor": "/Props/Static",
                "Foliage": "/Environment/Foliage",

                # Gameplay
                "PlayerStart": "/Gameplay/Spawn",
                "TriggerBox": "/Gameplay/Triggers/Box",
                "TriggerSphere": "/Gameplay/Triggers/Sphere",
                "TriggerVolume": "/Gameplay/Triggers/Volume",
                "NavMeshBoundsVolume": "/Gameplay/Navigation",

                # Cinematics
                "Camera": "/Cinematics/Cameras",
                "CineCameraActor": "/Cinematics/Cameras/Cine",

                # Audio
                "AmbientSound": "/Audio/Ambient",

                # Effects
                "ParticleSystem": "/Effects/Particles",
                "Niagara": "/Effects/Niagara",
            }

        # Get all actors in level
        all_actors = unreal.EditorLevelLibrary.get_all_level_actors()

        # Filter to target actors if specified
        if target_actors:
            all_actors = [a for a in all_actors if a and a.get_actor_label() in target_actors]

        organized_actors = []
        skipped_actors = []

        for actor in all_actors:
            if not actor:
                continue

            actor_name = actor.get_actor_label()
            actor_class = actor.get_class().get_name()

            # Find matching folder path
            folder_path = None
            for class_pattern, path in organization_rules.items():
                if class_pattern in actor_class:
                    folder_path = path
                    break

            if folder_path:
                # Set folder path for actor
                actor.set_folder_path(folder_path)
                organized_actors.append({
                    "name": actor_name,
                    "class": actor_class,
                    "folder": folder_path
                })
            else:
                skipped_actors.append({
                    "name": actor_name,
                    "class": actor_class,
                    "reason": "No matching organization rule"
                })

        # Generate folder summary
        folder_counts = {}
        for item in organized_actors:
            folder = item["folder"]
            folder_counts[folder] = folder_counts.get(folder, 0) + 1

        return {
            "success": True,
            "total_actors": len(all_actors),
            "organized_count": len(organized_actors),
            "skipped_count": len(skipped_actors),
            "folder_summary": folder_counts,
            "organized_actors": organized_actors[:20],
            "skipped_actors": skipped_actors[:10]
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to organize world outliner: {e}"}


def tag_assets(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add metadata tags to assets for organization and search.

    Args:
        asset_paths: List of asset paths to tag
        tags: List of tag strings to apply
        auto_tag: If True, automatically generate tags (optional)
    """
    import unreal

    asset_paths = data.get("asset_paths", [])
    tags = data.get("tags", [])
    auto_tag = data.get("auto_tag", False)

    if not asset_paths:
        return {"success": False, "error": "asset_paths is required"}

    try:
        tagged_assets = []
        failed_assets = []

        for asset_path in asset_paths:
            asset = unreal.load_asset(asset_path)
            if not asset:
                failed_assets.append({
                    "path": asset_path,
                    "reason": "Asset not found"
                })
                continue

            asset_name = asset.get_name()
            asset_class = asset.get_class().get_name()

            # Generate auto tags if requested
            applied_tags = list(tags)
            if auto_tag:
                auto_tags = []

                # Tag based on name patterns
                name_upper = asset_name.upper()
                if "FPS" in name_upper:
                    auto_tags.append("FPS")
                if "JUMP" in name_upper:
                    auto_tags.extend(["Movement", "Character"])
                if "FIRE" in name_upper or "SHOOT" in name_upper:
                    auto_tags.extend(["Combat", "Weapon"])
                if "MOVE" in name_upper or "WALK" in name_upper or "RUN" in name_upper:
                    auto_tags.append("Movement")
                if "LOOK" in name_upper or "AIM" in name_upper:
                    auto_tags.append("Camera")
                if "RELOAD" in name_upper:
                    auto_tags.extend(["Combat", "Weapon"])
                if "CROUCH" in name_upper:
                    auto_tags.extend(["Movement", "Character"])

                # Tag based on class
                if "Input" in asset_class:
                    auto_tags.append("Input")
                if "Blueprint" in asset_class:
                    auto_tags.append("Blueprint")
                if "Material" in asset_class:
                    auto_tags.append("Material")

                applied_tags.extend(auto_tags)

            # Remove duplicates
            applied_tags = list(set(applied_tags))

            # Apply tags as metadata
            for tag in applied_tags:
                unreal.EditorAssetLibrary.set_metadata_tag(asset, tag, "true")

            tagged_assets.append({
                "name": asset_name,
                "class": asset_class,
                "path": asset_path,
                "tags": applied_tags
            })

        return {
            "success": True,
            "tagged_count": len(tagged_assets),
            "failed_count": len(failed_assets),
            "auto_tag": auto_tag,
            "tagged_assets": tagged_assets,
            "failed_assets": failed_assets
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to tag assets: {e}"}


def search_assets_by_tag(data: Dict[str, Any]) -> Dict[str, Any]:
    """Search for assets with specific metadata tags.

    Args:
        folder_path: Folder to search in
        tags: List of tags to search for
        match_all: If True, asset must have ALL tags (optional)
    """
    import unreal

    folder_path = data.get("folder_path")
    tags = data.get("tags", [])
    match_all = data.get("match_all", False)

    if not folder_path:
        return {"success": False, "error": "folder_path is required"}

    if not tags:
        return {"success": False, "error": "tags list is required"}

    try:
        # Get all assets in folder
        assets = unreal.EditorAssetLibrary.list_assets(folder_path, recursive=True)

        matching_assets = []

        for asset_path in assets:
            asset = unreal.load_asset(asset_path)
            if not asset:
                continue

            asset_name = asset.get_name()
            asset_class = asset.get_class().get_name()

            # Check tags
            asset_tags = []
            for tag in tags:
                has_tag = unreal.EditorAssetLibrary.get_metadata_tag(asset, tag)
                if has_tag:
                    asset_tags.append(tag)

            # Determine if this asset matches
            if match_all:
                matches = len(asset_tags) == len(tags)
            else:
                matches = len(asset_tags) > 0

            if matches:
                matching_assets.append({
                    "name": asset_name,
                    "class": asset_class,
                    "path": asset_path,
                    "matched_tags": asset_tags
                })

        return {
            "success": True,
            "search_folder": folder_path,
            "search_tags": tags,
            "match_all": match_all,
            "total_assets_scanned": len(assets),
            "matching_count": len(matching_assets),
            "matching_assets": matching_assets
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to search assets: {e}"}


def generate_organization_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive organization report.

    Args:
        content_browser_paths: List of paths to analyze (optional)
        include_world_outliner: Include World Outliner stats (optional)
    """
    import unreal

    content_browser_paths = data.get("content_browser_paths", ["/Game"])
    include_world_outliner = data.get("include_world_outliner", True)

    try:
        report = {
            "content_browser": {},
            "world_outliner": {},
            "summary": {}
        }

        # Analyze Content Browser
        total_assets = 0
        assets_by_type = {}
        assets_by_folder = {}

        for base_path in content_browser_paths:
            # Get all assets recursively
            assets = unreal.EditorAssetLibrary.list_assets(base_path, recursive=True)
            total_assets += len(assets)

            for asset_path in assets:
                asset = unreal.load_asset(asset_path)
                if not asset:
                    continue

                asset_class = asset.get_class().get_name()

                # Count by type
                assets_by_type[asset_class] = assets_by_type.get(asset_class, 0) + 1

                # Count by folder (immediate parent folder)
                folder = "/".join(asset_path.split("/")[:-1])
                assets_by_folder[folder] = assets_by_folder.get(folder, 0) + 1

        report["content_browser"] = {
            "total_assets": total_assets,
            "assets_by_type": dict(sorted(assets_by_type.items(), key=lambda x: x[1], reverse=True)),
            "top_folders": dict(sorted(assets_by_folder.items(), key=lambda x: x[1], reverse=True)[:20])
        }

        # Analyze World Outliner
        if include_world_outliner:
            all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
            actors_by_class = {}
            actors_by_folder = {}
            organized_actors = 0
            unorganized_actors = 0

            for actor in all_actors:
                if not actor:
                    continue

                actor_class = actor.get_class().get_name()
                folder = str(actor.get_folder_path())

                # Count by class
                actors_by_class[actor_class] = actors_by_class.get(actor_class, 0) + 1

                # Count by folder
                if folder and folder != "None":
                    actors_by_folder[folder] = actors_by_folder.get(folder, 0) + 1
                    organized_actors += 1
                else:
                    unorganized_actors += 1

            total_actors = len(all_actors)
            report["world_outliner"] = {
                "total_actors": total_actors,
                "organized_actors": organized_actors,
                "unorganized_actors": unorganized_actors,
                "organization_percentage": round((organized_actors / total_actors * 100), 2) if total_actors > 0 else 0,
                "actors_by_class": dict(sorted(actors_by_class.items(), key=lambda x: x[1], reverse=True)[:15]),
                "actors_by_folder": dict(sorted(actors_by_folder.items(), key=lambda x: x[1], reverse=True)[:15])
            }

        # Generate summary
        report["summary"] = {
            "content_browser_total_assets": total_assets,
            "content_browser_asset_types": len(assets_by_type),
            "content_browser_folders": len(assets_by_folder),
            "world_outliner_total_actors": report["world_outliner"].get("total_actors", 0),
            "world_outliner_organized_percentage": report["world_outliner"].get("organization_percentage", 0)
        }

        return {
            "success": True,
            "report": report
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to generate report: {e}"}
