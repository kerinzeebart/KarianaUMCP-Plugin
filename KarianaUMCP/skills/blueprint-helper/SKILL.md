---
name: blueprint-helper
description: Create, modify, and manage Unreal Engine Blueprints programmatically
version: 1.0.0
author: KarianaUMCP
dependencies:
  - unreal
---

# Blueprint Helper Skill

Create and manipulate Unreal Engine Blueprints programmatically, enabling rapid prototyping and automated Blueprint generation.

## Capabilities

- Create new Blueprint classes
- Add components to Blueprints
- Set default properties
- Create Blueprint from existing actors
- Compile and save Blueprints
- List Blueprint components and variables

## Usage

### Create Empty Blueprint

```python
create_blueprint(
    name="BP_MyActor",
    parent_class="Actor",
    save_path="/Game/Blueprints"
)
```

### Add Component to Blueprint

```python
add_blueprint_component(
    blueprint_path="/Game/Blueprints/BP_MyActor",
    component_type="StaticMeshComponent",
    component_name="Mesh"
)
```

### Create Blueprint from Actor

```python
create_blueprint_from_actor(
    actor_name="Cube_1",
    blueprint_name="BP_FromCube",
    save_path="/Game/Blueprints"
)
```

## Parameters

### create_blueprint

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | string | Yes | Blueprint asset name |
| parent_class | string | No | Parent class (default: Actor) |
| save_path | string | No | Asset path (default: /Game/Blueprints) |

### add_blueprint_component

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| blueprint_path | string | Yes | Full asset path to Blueprint |
| component_type | string | Yes | Component class name |
| component_name | string | No | Name for component |
| attach_to | string | No | Parent component name |

### create_blueprint_from_actor

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| actor_name | string | Yes | Actor name in level |
| blueprint_name | string | Yes | Name for new Blueprint |
| save_path | string | No | Where to save |

## Component Types

Common component types you can add:

- `StaticMeshComponent` - Static geometry
- `SkeletalMeshComponent` - Animated meshes
- `PointLightComponent` - Point light
- `SpotLightComponent` - Spot light
- `BoxCollisionComponent` - Box collision
- `SphereCollisionComponent` - Sphere collision
- `AudioComponent` - Sound playback
- `ParticleSystemComponent` - Particle effects
- `CameraComponent` - Camera
- `SceneComponent` - Transform hierarchy
- `ArrowComponent` - Directional indicator

## Examples

### Interactive Object Blueprint

```python
# Create base Blueprint
create_blueprint(
    name="BP_Interactive",
    parent_class="Actor",
    save_path="/Game/Blueprints/Gameplay"
)

# Add mesh component
add_blueprint_component(
    blueprint_path="/Game/Blueprints/Gameplay/BP_Interactive",
    component_type="StaticMeshComponent",
    component_name="InteractiveMesh"
)

# Add collision
add_blueprint_component(
    blueprint_path="/Game/Blueprints/Gameplay/BP_Interactive",
    component_type="BoxCollisionComponent",
    component_name="InteractionZone"
)
```

### Light Blueprint

```python
create_blueprint(name="BP_CustomLight", parent_class="Actor")

add_blueprint_component(
    blueprint_path="/Game/Blueprints/BP_CustomLight",
    component_type="PointLightComponent",
    component_name="MainLight"
)

add_blueprint_component(
    blueprint_path="/Game/Blueprints/BP_CustomLight",
    component_type="SphereCollisionComponent",
    component_name="LightRadius"
)
```

### Convert Level Design to Blueprint

```python
# After designing a prop arrangement in the level
create_blueprint_from_actor(
    actor_name="PropCluster_1",
    blueprint_name="BP_PropCluster",
    save_path="/Game/Blueprints/Props"
)
```

## Response Format

```json
{
  "success": true,
  "blueprint_path": "/Game/Blueprints/BP_MyActor",
  "components": ["DefaultSceneRoot", "Mesh"],
  "compiled": true
}
```

## Error Handling

- Returns `{"success": false, "error": "..."}` on failure
- Common errors:
  - Blueprint already exists
  - Invalid parent class
  - Component type not found
  - Actor not found (for create_from_actor)

## Best Practices

1. Always use descriptive Blueprint names with BP_ prefix
2. Organize Blueprints in logical folder hierarchies
3. Create Blueprints from proven level designs
4. Add collision components for interactive objects
5. Test Blueprints after creation

## Related Skills

- `spawn-actor` - Spawn instances of created Blueprints
- `level-organizer` - Organize Blueprint actors in level
