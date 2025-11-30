"""
KarianaUMCP Blueprint Operations
================================
Blueprint creation and manipulation tools.

Supports:
- create_blueprint
- add_blueprint_component
- get_blueprint_info
- compile_blueprint
- open_blueprint_editor
- create_blueprint_from_actor
"""

from typing import Dict, Any, List, Optional
import traceback


def handle_blueprint_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route blueprint commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "create_blueprint": create_blueprint,
        "add_blueprint_component": add_blueprint_component,
        "get_blueprint_info": get_blueprint_info,
        "compile_blueprint": compile_blueprint,
        "open_blueprint_editor": open_blueprint_editor,
        "create_blueprint_from_actor": create_blueprint_from_actor,
        "set_component_property": set_component_property,
        "set_component_transform": set_component_transform,
        "get_blueprint_components": get_blueprint_components,
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
        return {"success": False, "error": f"Unknown blueprint command: {cmd}"}


def create_blueprint(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new Blueprint"""
    import unreal

    name = data.get("name", "NewBlueprint")
    path = data.get("path", "/Game/Blueprints")
    parent_class = data.get("parent_class", "Actor")

    # Ensure path ends with the blueprint name
    if not path.endswith(name):
        full_path = f"{path}/{name}"
    else:
        full_path = path

    # Map common parent class names
    class_mapping = {
        "Actor": "/Script/Engine.Actor",
        "Pawn": "/Script/Engine.Pawn",
        "Character": "/Script/Engine.Character",
        "PlayerController": "/Script/Engine.PlayerController",
        "GameModeBase": "/Script/Engine.GameModeBase",
        "ActorComponent": "/Script/Engine.ActorComponent",
        "SceneComponent": "/Script/Engine.SceneComponent",
    }

    parent_path = class_mapping.get(parent_class, f"/Script/Engine.{parent_class}")

    try:
        # Load parent class
        parent = unreal.load_class(None, parent_path)
        if not parent:
            return {"success": False, "error": f"Could not load parent class: {parent_path}"}

        # Create the Blueprint
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent)  # Use set_editor_property for UE5

        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        blueprint = asset_tools.create_asset(name, path, None, factory)  # Let factory determine class

        if not blueprint:
            return {"success": False, "error": "Failed to create Blueprint"}

        # Compile and save - use BlueprintEditorLibrary (not KismetSystemLibrary)
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        unreal.EditorAssetLibrary.save_asset(full_path)

        # Auto-open in editor
        asset_editor = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        asset_editor.open_editor_for_assets([blueprint])  # UE5 uses plural form with array

        return {
            "success": True,
            "blueprint": name,
            "path": full_path,
            "parent_class": parent_class,
            "opened": True,
            "message": "Blueprint created and opened in editor"
        }

    except Exception as e:
        return {"success": False, "error": f"Blueprint creation failed: {e}"}


def add_blueprint_component(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a component to a Blueprint using UE5 SubobjectDataSubsystem"""
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    component_type = data.get("component_class", "") or data.get("component_type", "StaticMeshComponent")
    component_name = data.get("component_name", "") or data.get("name", "NewComponent")
    parent_component = data.get("parent", None)

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    # Normalize path
    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    try:
        # Load the Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Verify it's actually a Blueprint
        if not isinstance(blueprint, unreal.Blueprint):
            return {"success": False, "error": f"Asset is not a Blueprint: {blueprint_path}"}

        # Get SubobjectDataSubsystem - UE5's API for adding components to blueprints
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        if not sds:
            return {"success": False, "error": "Failed to get SubobjectDataSubsystem"}

        # Map component class names to unreal classes
        class_mapping = {
            "StaticMeshComponent": unreal.StaticMeshComponent,
            "SkeletalMeshComponent": unreal.SkeletalMeshComponent,
            "SceneComponent": unreal.SceneComponent,
            "PointLightComponent": unreal.PointLightComponent,
            "SpotLightComponent": unreal.SpotLightComponent,
            "DirectionalLightComponent": unreal.DirectionalLightComponent,
            "CameraComponent": unreal.CameraComponent,
            "BoxComponent": unreal.BoxComponent,
            "SphereComponent": unreal.SphereComponent,
            "CapsuleComponent": unreal.CapsuleComponent,
            "ArrowComponent": unreal.ArrowComponent,
            "AudioComponent": unreal.AudioComponent,
            "ChildActorComponent": unreal.ChildActorComponent,
            "TextRenderComponent": unreal.TextRenderComponent,
            "BillboardComponent": unreal.BillboardComponent,
            "SpringArmComponent": unreal.SpringArmComponent,
        }

        # Get component class
        comp_class = class_mapping.get(component_type)
        if not comp_class:
            # Try to get the class dynamically
            try:
                comp_class = getattr(unreal, component_type, None)
            except AttributeError:
                pass

        if not comp_class:
            return {"success": False, "error": f"Component class not found: {component_type}"}

        # Get existing subobjects to find root handle
        handles = sds.k2_gather_subobject_data_for_blueprint(blueprint)
        root_handle = None

        for h in handles:
            sd = sds.k2_find_subobject_data_from_handle(h)
            if sd and unreal.SubobjectDataBlueprintFunctionLibrary.is_root_component(sd):
                root_handle = h
                break

        # Find parent handle if specified
        parent_handle = root_handle  # Default to root
        if parent_component:
            for h in handles:
                sd = sds.k2_find_subobject_data_from_handle(h)
                if sd:
                    name = unreal.SubobjectDataBlueprintFunctionLibrary.get_display_name(sd)
                    if name == parent_component:
                        parent_handle = h
                        break

        # Create params for adding new subobject
        params = unreal.AddNewSubobjectParams()
        params.set_editor_property('blueprint_context', blueprint)
        params.set_editor_property('new_class', comp_class.static_class())
        if parent_handle:
            params.set_editor_property('parent_handle', parent_handle)

        # Add the component
        new_handle, fail_reason = sds.add_new_subobject(params)

        # fail_reason is Text type - check if it has content
        fail_str = str(fail_reason) if fail_reason else ""
        if fail_str and fail_str.strip():
            return {"success": False, "error": f"Failed to add component: {fail_str}"}

        # Compile blueprint to apply changes
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)

        # Save the blueprint
        unreal.EditorAssetLibrary.save_asset(blueprint_path)

        # Re-open editor to show changes
        asset_editor = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        asset_editor.open_editor_for_assets([blueprint])

        return {
            "success": True,
            "blueprint": blueprint_path,
            "component": component_name,
            "component_type": component_type,
            "parent": parent_component,
            "message": f"Added {component_type} '{component_name}' to blueprint and opened editor"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to add component: {e}",
            "traceback": traceback.format_exc()
        }


def get_blueprint_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get information about a Blueprint"""
    import unreal

    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    # Normalize path
    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    try:
        # Load the Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Get Blueprint info
        info = {
            "success": True,
            "path": blueprint_path,
            "name": blueprint.get_name(),
            "class": blueprint.get_class().get_name(),
        }

        # Try to get parent class
        try:
            parent = blueprint.get_editor_property("parent_class")
            if parent:
                info["parent_class"] = parent.get_name()
        except (AttributeError, RuntimeError):
            pass

        # Try to get generated class
        try:
            gen_class = blueprint.get_editor_property("generated_class")
            if gen_class:
                info["generated_class"] = gen_class.get_name()
        except (AttributeError, RuntimeError):
            pass

        return info

    except Exception as e:
        return {"success": False, "error": f"Failed to get Blueprint info: {e}"}


def compile_blueprint(data: Dict[str, Any]) -> Dict[str, Any]:
    """Compile a Blueprint"""
    import unreal

    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    # Normalize path
    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    try:
        # Load the Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Compile - use BlueprintEditorLibrary (not KismetSystemLibrary)
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)

        # Save
        unreal.EditorAssetLibrary.save_asset(blueprint_path)

        return {
            "success": True,
            "blueprint": blueprint_path,
            "message": "Blueprint compiled and saved"
        }

    except Exception as e:
        return {"success": False, "error": f"Compilation failed: {e}"}


def open_blueprint_editor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Open a Blueprint in the editor"""
    import unreal

    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    # Normalize path
    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    try:
        # Load the Blueprint
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Open in editor
        unreal.AssetEditorSubsystem().open_editor_for_assets([blueprint])

        return {
            "success": True,
            "blueprint": blueprint_path,
            "message": "Blueprint editor opened"
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to open editor: {e}"}


def create_blueprint_from_actor(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Blueprint from an existing actor"""
    import unreal

    actor_name = data.get("actor_name", "")
    blueprint_name = data.get("blueprint_name", "")
    blueprint_path = data.get("path", "/Game/Blueprints")

    if not actor_name:
        return {"success": False, "error": "actor_name is required"}

    if not blueprint_name:
        blueprint_name = f"BP_{actor_name}"

    try:
        # Find the actor
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        target_actor = None

        for actor in actors:
            if actor.get_actor_label() == actor_name:
                target_actor = actor
                break

        if not target_actor:
            return {"success": False, "error": f"Actor not found: {actor_name}"}

        # Create Blueprint from actor
        full_path = f"{blueprint_path}/{blueprint_name}"

        # Use editor functionality to create Blueprint from actor
        unreal.EditorLevelLibrary.create_blueprint_from_actor(full_path, target_actor, True)

        return {
            "success": True,
            "actor": actor_name,
            "blueprint": blueprint_name,
            "path": full_path
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to create Blueprint: {e}"}


def set_component_property(data: Dict[str, Any]) -> Dict[str, Any]:
    """Set a property on a blueprint component using UE5 SubobjectDataSubsystem"""
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    component_name = data.get("component_name", "")
    property_name = data.get("property", "") or data.get("property_name", "")
    value = data.get("value")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}
    if not component_name:
        return {"success": False, "error": "component_name is required"}
    if not property_name:
        return {"success": False, "error": "property is required"}

    # Normalize path
    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    try:
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Get SubobjectDataSubsystem
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        if not sds:
            return {"success": False, "error": "Failed to get SubobjectDataSubsystem"}

        sdbfl = unreal.SubobjectDataBlueprintFunctionLibrary
        handles = sds.k2_gather_subobject_data_for_blueprint(blueprint)

        # Find the component
        for h in handles:
            sd = sds.k2_find_subobject_data_from_handle(h)
            if sd:
                name = str(sdbfl.get_display_name(sd))  # Convert Text to string
                if name == component_name:
                    template = sdbfl.get_object(sd)
                    if template and hasattr(template, property_name):
                        template.set_editor_property(property_name, value)
                        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
                        unreal.EditorAssetLibrary.save_asset(blueprint_path)
                        return {
                            "success": True,
                            "blueprint": blueprint_path,
                            "component": component_name,
                            "property": property_name,
                            "value": str(value),
                            "message": f"Set {property_name} on {component_name}"
                        }
                    else:
                        return {"success": False, "error": f"Property '{property_name}' not found on component"}

        return {"success": False, "error": f"Component not found: {component_name}"}

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to set property: {e}",
            "traceback": traceback.format_exc()
        }


def set_component_transform(data: Dict[str, Any]) -> Dict[str, Any]:
    """Set transform (location/rotation/scale) on a blueprint component using UE5 SubobjectDataSubsystem"""
    import unreal

    blueprint_path = data.get("blueprint_path", "")
    component_name = data.get("component_name", "")
    location = data.get("location")  # [x, y, z]
    rotation = data.get("rotation")  # [pitch, yaw, roll]
    scale = data.get("scale")  # [x, y, z]

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}
    if not component_name:
        return {"success": False, "error": "component_name is required"}

    # Validate array lengths
    if location and (not isinstance(location, (list, tuple)) or len(location) != 3):
        return {"success": False, "error": "location must be an array of 3 values [x, y, z]"}
    if rotation and (not isinstance(rotation, (list, tuple)) or len(rotation) != 3):
        return {"success": False, "error": "rotation must be an array of 3 values [pitch, yaw, roll]"}
    if scale and (not isinstance(scale, (list, tuple)) or len(scale) != 3):
        return {"success": False, "error": "scale must be an array of 3 values [x, y, z]"}

    # Normalize path
    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    try:
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Get SubobjectDataSubsystem
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        if not sds:
            return {"success": False, "error": "Failed to get SubobjectDataSubsystem"}

        sdbfl = unreal.SubobjectDataBlueprintFunctionLibrary
        handles = sds.k2_gather_subobject_data_for_blueprint(blueprint)

        # Find the component
        for h in handles:
            sd = sds.k2_find_subobject_data_from_handle(h)
            if sd:
                name = str(sdbfl.get_display_name(sd))  # Convert Text to string
                if name == component_name:
                    template = sdbfl.get_object(sd)
                    if not template:
                        return {"success": False, "error": f"Could not get template for component: {component_name}"}

                    changes = []

                    # Set location
                    if location and hasattr(template, 'relative_location'):
                        loc = unreal.Vector(float(location[0]), float(location[1]), float(location[2]))
                        template.set_editor_property('relative_location', loc)
                        changes.append(f"location={location}")

                    # Set rotation
                    if rotation and hasattr(template, 'relative_rotation'):
                        rot = unreal.Rotator(float(rotation[0]), float(rotation[1]), float(rotation[2]))
                        template.set_editor_property('relative_rotation', rot)
                        changes.append(f"rotation={rotation}")

                    # Set scale
                    if scale and hasattr(template, 'relative_scale3d'):
                        sc = unreal.Vector(float(scale[0]), float(scale[1]), float(scale[2]))
                        template.set_editor_property('relative_scale3d', sc)
                        changes.append(f"scale={scale}")

                    if changes:
                        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
                        unreal.EditorAssetLibrary.save_asset(blueprint_path)
                        return {
                            "success": True,
                            "blueprint": blueprint_path,
                            "component": component_name,
                            "changes": changes,
                            "message": f"Transform updated: {', '.join(changes)}"
                        }
                    else:
                        return {"success": False, "error": "No transform values provided"}

        return {"success": False, "error": f"Component not found: {component_name}"}

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to set transform: {e}",
            "traceback": traceback.format_exc()
        }


def get_blueprint_components(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get list of components in a blueprint using UE5 SubobjectDataSubsystem"""
    import unreal

    blueprint_path = data.get("blueprint_path", "") or data.get("path", "")

    if not blueprint_path:
        return {"success": False, "error": "blueprint_path is required"}

    # Normalize path
    if not blueprint_path.startswith("/Game"):
        blueprint_path = f"/Game/{blueprint_path}"

    try:
        blueprint = unreal.load_asset(blueprint_path)
        if not blueprint:
            return {"success": False, "error": f"Blueprint not found: {blueprint_path}"}

        # Get SubobjectDataSubsystem
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        if not sds:
            return {"success": False, "error": "Failed to get SubobjectDataSubsystem"}

        sdbfl = unreal.SubobjectDataBlueprintFunctionLibrary
        handles = sds.k2_gather_subobject_data_for_blueprint(blueprint)

        components = []
        seen_names = set()  # Track unique components

        for h in handles:
            sd = sds.k2_find_subobject_data_from_handle(h)
            if sd:
                name = str(sdbfl.get_display_name(sd))  # Convert Text to string for hashing

                # Skip duplicates and the root actor object
                if name in seen_names:
                    continue
                seen_names.add(name)

                is_component = sdbfl.is_component(sd)
                is_root = sdbfl.is_root_component(sd)

                # Skip non-component entries (like the actor itself)
                if not is_component:
                    continue

                template = sdbfl.get_object(sd)
                comp_type = template.get_class().get_name() if template else "Unknown"

                comp_info = {
                    "name": name,
                    "type": comp_type,
                    "is_root": is_root
                }

                # Get transform if available
                if template and hasattr(template, 'relative_location'):
                    try:
                        loc = template.get_editor_property('relative_location')
                        comp_info["location"] = {"x": loc.x, "y": loc.y, "z": loc.z}
                    except (AttributeError, RuntimeError):
                        pass

                components.append(comp_info)

        return {
            "success": True,
            "blueprint": blueprint_path,
            "components": components,
            "count": len(components)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get components: {e}",
            "traceback": traceback.format_exc()
        }
