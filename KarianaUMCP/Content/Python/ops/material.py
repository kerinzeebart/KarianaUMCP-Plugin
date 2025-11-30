"""
KarianaUMCP Material Operations
===============================
Material creation and management tools.

Supports:
- list_materials
- get_material_info
- create_material_instance
- apply_material_to_actor
- create_simple_material
"""

from typing import Dict, Any, List, Optional
import traceback


def handle_material_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route material commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "list_materials": list_materials,
        "get_material_info": get_material_info,
        "create_material_instance": create_material_instance,
        "apply_material_to_actor": apply_material_to_actor,
        "create_simple_material": create_simple_material,
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
        return {"success": False, "error": f"Unknown material command: {cmd}"}


def _find_actor_by_name(actor_name: str):
    """Helper to find actor by label"""
    import unreal
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in actors:
        if actor.get_actor_label() == actor_name:
            return actor
    return None


def list_materials(data: Dict[str, Any]) -> Dict[str, Any]:
    """List materials in a given path with optional name filtering.

    Args:
        path: Content browser path to search (default: "/Game")
        pattern: Optional pattern to filter material names
        limit: Maximum number of materials to return (default: 50)
    """
    import unreal

    path = data.get("path", "/Game")
    pattern = data.get("pattern", "")
    limit = data.get("limit", 50)

    try:
        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

        # Get all assets by path, then filter for materials
        all_assets = asset_registry.get_assets_by_path(path, recursive=True)

        # Filter for material types
        assets = []
        for asset in all_assets:
            try:
                asset_type = str(asset.asset_class_path.asset_name) if hasattr(
                    asset.asset_class_path, 'asset_name'
                ) else str(asset.asset_class_path)

                if asset_type in ['Material', 'MaterialInstance', 'MaterialInstanceConstant']:
                    assets.append(asset)
            except:
                pass

        # Apply pattern filter if specified
        filtered_assets = assets
        if pattern:
            filtered_assets = []
            pattern_lower = pattern.lower()
            for asset in assets:
                asset_name = str(asset.asset_name).lower()
                if pattern_lower in asset_name:
                    filtered_assets.append(asset)

        # Build material list with limit
        material_list = []
        for i, asset in enumerate(filtered_assets):
            if i >= limit:
                break

            try:
                asset_type = str(asset.asset_class_path.asset_name) if hasattr(
                    asset.asset_class_path, 'asset_name'
                ) else str(asset.asset_class_path)
            except:
                asset_type = "Unknown"

            material_info = {
                "name": str(asset.asset_name),
                "path": str(asset.package_name),
                "type": asset_type
            }

            material_list.append(material_info)

        return {
            "success": True,
            "materials": material_list,
            "total_count": len(filtered_assets),
            "returned_count": len(material_list),
            "path": path,
            "pattern": pattern if pattern else None
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to list materials: {e}"}


def get_material_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed information about a material.

    Args:
        material_path: Path to the material
    """
    import unreal

    material_path = data.get("material_path", "") or data.get("path", "")

    if not material_path:
        return {"success": False, "error": "material_path is required"}

    # Normalize path
    if not material_path.startswith("/Game"):
        material_path = f"/Game/{material_path}"

    try:
        # Check if material exists
        if not unreal.EditorAssetLibrary.does_asset_exist(material_path):
            return {"success": False, "error": f"Material does not exist: {material_path}"}

        # Load the material
        material = unreal.load_asset(material_path)
        if not material:
            return {"success": False, "error": f"Failed to load material: {material_path}"}

        info = {
            "success": True,
            "material_path": material_path,
            "material_type": material.get_class().get_name(),
            "name": str(material.get_name())
        }

        # Get basic material properties
        try:
            if hasattr(material, 'get_editor_property'):
                info["domain"] = str(material.get_editor_property('material_domain'))
                info["blend_mode"] = str(material.get_editor_property('blend_mode'))
                info["shading_model"] = str(material.get_editor_property('shading_model'))
                info["two_sided"] = bool(material.get_editor_property('two_sided'))
        except Exception:
            pass

        # Handle Material Instance specific info
        if isinstance(material, (unreal.MaterialInstance, unreal.MaterialInstanceConstant)):
            try:
                # Get parent material
                parent = material.get_editor_property('parent')
                if parent:
                    info["parent_material"] = str(parent.get_path_name())

                # Get scalar parameters
                scalar_params = []
                try:
                    scalar_param_names = material.get_scalar_parameter_names()
                    for param_name in scalar_param_names:
                        value = material.get_scalar_parameter_value(param_name)
                        scalar_params.append({
                            "name": str(param_name),
                            "value": float(value)
                        })
                except Exception:
                    pass

                info["scalar_parameters"] = scalar_params

                # Get vector parameters
                vector_params = []
                try:
                    vector_param_names = material.get_vector_parameter_names()
                    for param_name in vector_param_names:
                        value = material.get_vector_parameter_value(param_name)
                        vector_params.append({
                            "name": str(param_name),
                            "value": {
                                "r": float(value.r),
                                "g": float(value.g),
                                "b": float(value.b),
                                "a": float(value.a)
                            }
                        })
                except Exception:
                    pass

                info["vector_parameters"] = vector_params

                # Get texture parameters
                texture_params = []
                try:
                    texture_param_names = material.get_texture_parameter_names()
                    for param_name in texture_param_names:
                        texture = material.get_texture_parameter_value(param_name)
                        texture_params.append({
                            "name": str(param_name),
                            "texture": str(texture.get_path_name()) if texture else None
                        })
                except Exception:
                    pass

                info["texture_parameters"] = texture_params

            except Exception:
                pass

        return info

    except Exception as e:
        return {"success": False, "error": f"Failed to get material info: {e}"}


def create_material_instance(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new material instance from a parent material.

    Args:
        parent_material_path: Path to the parent material
        instance_name: Name for the new material instance
        target_folder: Destination folder in content browser (default: "/Game/Materials")
        parameters: Dictionary of parameter overrides to set
    """
    import unreal

    parent_material_path = data.get("parent_material_path", "")
    instance_name = data.get("instance_name", "")
    target_folder = data.get("target_folder", "/Game/Materials")
    parameters = data.get("parameters", {})

    if not parent_material_path:
        return {"success": False, "error": "parent_material_path is required"}
    if not instance_name:
        return {"success": False, "error": "instance_name is required"}

    # Normalize paths
    if not parent_material_path.startswith("/Game"):
        parent_material_path = f"/Game/{parent_material_path}"

    try:
        # Validate parent material exists
        if not unreal.EditorAssetLibrary.does_asset_exist(parent_material_path):
            return {"success": False, "error": f"Parent material does not exist: {parent_material_path}"}

        parent_material = unreal.load_asset(parent_material_path)
        if not parent_material:
            return {"success": False, "error": f"Failed to load parent material: {parent_material_path}"}

        # Create the target path
        target_path = f"{target_folder}/{instance_name}"

        # Check if material instance already exists
        if unreal.EditorAssetLibrary.does_asset_exist(target_path):
            return {"success": False, "error": f"Material instance already exists: {target_path}"}

        # Create material instance using AssetTools
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

        # Create material instance constant
        material_instance = asset_tools.create_asset(
            asset_name=instance_name,
            package_path=target_folder,
            asset_class=unreal.MaterialInstanceConstant,
            factory=unreal.MaterialInstanceConstantFactoryNew()
        )

        if not material_instance:
            return {"success": False, "error": "Failed to create material instance asset"}

        # Set parent material
        material_instance.set_editor_property('parent', parent_material)

        # Apply parameter overrides if provided
        if parameters:
            _apply_material_parameters(material_instance, parameters)

        # Save the asset
        unreal.EditorAssetLibrary.save_asset(target_path)

        return {
            "success": True,
            "material_instance_path": target_path,
            "parent_material": parent_material_path,
            "name": instance_name,
            "applied_parameters": list(parameters.keys()) if parameters else []
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to create material instance: {e}"}


def apply_material_to_actor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a material to a specific material slot on an actor.

    Args:
        actor_name: Name of the actor to modify
        material_path: Path to the material to apply
        slot_index: Material slot index (default: 0)
    """
    import unreal

    actor_name = data.get("actor_name", "")
    material_path = data.get("material_path", "")
    slot_index = data.get("slot_index", 0)

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}
    if not material_path:
        return {"success": False, "error": "material_path is required"}

    # Normalize path
    if not material_path.startswith("/Game"):
        material_path = f"/Game/{material_path}"

    try:
        # Find the actor by name
        actor = _find_actor_by_name(actor_name)
        if not actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        # Load the material
        if not unreal.EditorAssetLibrary.does_asset_exist(material_path):
            return {"success": False, "error": f"Material does not exist: {material_path}"}

        material = unreal.load_asset(material_path)
        if not material:
            return {"success": False, "error": f"Failed to load material: {material_path}"}

        # Get the static mesh component
        static_mesh_component = None

        # Try different ways to get the mesh component
        if hasattr(actor, 'static_mesh_component'):
            static_mesh_component = actor.static_mesh_component
        elif hasattr(actor, 'get_component_by_class'):
            static_mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
        else:
            # Get components and find first StaticMeshComponent
            components = actor.get_components_by_class(unreal.StaticMeshComponent)
            if components and len(components) > 0:
                static_mesh_component = components[0]

        if not static_mesh_component:
            return {"success": False, "error": f"No static mesh component found on actor: {actor_name}"}

        # Apply the material to the specified slot
        static_mesh_component.set_material(slot_index, material)

        return {
            "success": True,
            "actor_name": actor_name,
            "material_path": material_path,
            "slot_index": slot_index,
            "component_name": static_mesh_component.get_name()
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to apply material to actor: {e}"}


def create_simple_material(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a simple material with basic parameters.

    Args:
        material_name: Name for the new material
        target_folder: Destination folder in content browser (default: "/Game/Materials")
        base_color: RGB color values (0-1 range) e.g. {"r": 1.0, "g": 0.5, "b": 0.0}
        metallic: Metallic value (0-1) (default: 0.0)
        roughness: Roughness value (0-1) (default: 0.5)
        emissive: RGB emissive color values (0-1 range)
    """
    import unreal

    material_name = data.get("material_name", "")
    target_folder = data.get("target_folder", "/Game/Materials")
    base_color = data.get("base_color")
    metallic = data.get("metallic", 0.0)
    roughness = data.get("roughness", 0.5)
    emissive = data.get("emissive")

    if not material_name:
        return {"success": False, "error": "material_name is required"}

    try:
        # Create the target path
        target_path = f"{target_folder}/{material_name}"

        # Check if material already exists
        if unreal.EditorAssetLibrary.does_asset_exist(target_path):
            return {"success": False, "error": f"Material already exists: {target_path}"}

        # Ensure target folder exists
        if not unreal.EditorAssetLibrary.does_directory_exist(target_folder):
            unreal.EditorAssetLibrary.make_directory(target_folder)

        # Create material using AssetTools
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

        material = asset_tools.create_asset(
            asset_name=material_name,
            package_path=target_folder,
            asset_class=unreal.Material,
            factory=unreal.MaterialFactoryNew()
        )

        if not material:
            return {"success": False, "error": "Failed to create material asset"}

        # Set basic material properties
        material.set_editor_property('two_sided', False)

        # Create and connect material expression nodes
        material_editor = unreal.MaterialEditingLibrary

        # Base Color
        if base_color:
            color_node = unreal.MaterialEditingLibrary.create_material_expression(
                material, unreal.MaterialExpressionVectorParameter
            )
            color_node.set_editor_property('parameter_name', 'BaseColor')
            color_node.set_editor_property('default_value',
                unreal.LinearColor(
                    base_color.get('r', 1.0),
                    base_color.get('g', 1.0),
                    base_color.get('b', 1.0),
                    1.0
                )
            )

            # Connect to base color
            material_editor.connect_material_property(
                color_node, '', unreal.MaterialProperty.MP_BASE_COLOR
            )

        # Metallic
        if metallic != 0.0:
            metallic_node = unreal.MaterialEditingLibrary.create_material_expression(
                material, unreal.MaterialExpressionScalarParameter
            )
            metallic_node.set_editor_property('parameter_name', 'Metallic')
            metallic_node.set_editor_property('default_value', metallic)

            material_editor.connect_material_property(
                metallic_node, '', unreal.MaterialProperty.MP_METALLIC
            )

        # Roughness
        roughness_node = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionScalarParameter
        )
        roughness_node.set_editor_property('parameter_name', 'Roughness')
        roughness_node.set_editor_property('default_value', roughness)

        material_editor.connect_material_property(
            roughness_node, '', unreal.MaterialProperty.MP_ROUGHNESS
        )

        # Emissive
        if emissive:
            emissive_node = unreal.MaterialEditingLibrary.create_material_expression(
                material, unreal.MaterialExpressionVectorParameter
            )
            emissive_node.set_editor_property('parameter_name', 'EmissiveColor')
            emissive_node.set_editor_property('default_value',
                unreal.LinearColor(
                    emissive.get('r', 0.0),
                    emissive.get('g', 0.0),
                    emissive.get('b', 0.0),
                    1.0
                )
            )

            material_editor.connect_material_property(
                emissive_node, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR
            )

        # Recompile the material
        unreal.MaterialEditingLibrary.recompile_material(material)

        # Save the asset
        unreal.EditorAssetLibrary.save_asset(target_path)

        return {
            "success": True,
            "material_path": target_path,
            "name": material_name,
            "properties": {
                "base_color": base_color,
                "metallic": metallic,
                "roughness": roughness,
                "emissive": emissive
            }
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to create simple material: {e}"}


def _apply_material_parameters(material_instance, parameters: Dict[str, Any]):
    """Apply parameter overrides to a material instance."""
    import unreal

    for param_name, param_value in parameters.items():
        try:
            if isinstance(param_value, (int, float)):
                # Scalar parameter
                material_instance.set_scalar_parameter_value(param_name, float(param_value))
            elif isinstance(param_value, dict) and all(k in param_value for k in ['r', 'g', 'b']):
                # Vector parameter (color)
                color = unreal.LinearColor(
                    param_value['r'],
                    param_value['g'],
                    param_value['b'],
                    param_value.get('a', 1.0)
                )
                material_instance.set_vector_parameter_value(param_name, color)
            elif isinstance(param_value, str):
                # Texture parameter
                if unreal.EditorAssetLibrary.does_asset_exist(param_value):
                    texture = unreal.load_asset(param_value)
                    if texture:
                        material_instance.set_texture_parameter_value(param_name, texture)
        except Exception:
            pass
