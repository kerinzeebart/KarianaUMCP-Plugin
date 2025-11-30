---
name: spawn-actor
description: Spawn and manipulate actors in Unreal Engine levels with precise positioning
version: 1.0.0
author: KarianaUMCP
dependencies:
  - unreal
  - socket_server
---

# Spawn Actor Skill

Spawn actors, primitives, and objects in Unreal Engine with precise control over position, rotation, scale, and properties.

## Capabilities

- Spawn basic primitives (Cube, Sphere, Cylinder, Cone, Plane)
- Spawn static meshes from asset paths
- Spawn Blueprint actors
- Set transform (location, rotation, scale)
- Set material and physics properties
- Batch spawn multiple actors

## Usage

### Basic Primitive Spawn

```python
# Via MCP tool call
spawn_actor(
    actor_type="Cube",
    location=[0, 0, 100],
    scale=[1, 1, 1]
)
```

### Spawn with Material

```python
spawn_actor(
    actor_type="Sphere",
    location=[500, 0, 100],
    material="/Game/Materials/M_Red"
)
```

### Spawn Blueprint Actor

```python
spawn_actor(
    blueprint_path="/Game/Blueprints/BP_Interactive",
    location=[0, 500, 0],
    rotation=[0, 45, 0]
)
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| actor_type | string | No | Primitive type: Cube, Sphere, Cylinder, Cone, Plane |
| blueprint_path | string | No | Path to Blueprint asset |
| location | array[3] | No | [X, Y, Z] world location (default: [0, 0, 0]) |
| rotation | array[3] | No | [Pitch, Yaw, Roll] in degrees (default: [0, 0, 0]) |
| scale | array[3] | No | [X, Y, Z] scale (default: [1, 1, 1]) |
| material | string | No | Material asset path |
| simulate_physics | bool | No | Enable physics simulation |
| name | string | No | Custom actor label |

## Examples

### Create a Scene

```python
# Floor
spawn_actor(actor_type="Plane", location=[0, 0, 0], scale=[10, 10, 1])

# Table
spawn_actor(actor_type="Cube", location=[0, 0, 50], scale=[2, 1, 0.1])

# Objects on table
spawn_actor(actor_type="Sphere", location=[-50, 0, 100], scale=[0.3, 0.3, 0.3])
spawn_actor(actor_type="Cylinder", location=[50, 0, 100], scale=[0.2, 0.2, 0.5])
```

### Physics Demo

```python
# Spawn stacked boxes that will fall
for i in range(5):
    spawn_actor(
        actor_type="Cube",
        location=[0, 0, 100 + i * 110],
        scale=[1, 1, 1],
        simulate_physics=True
    )
```

## Error Handling

- Returns `{"success": false, "error": "..."}` on failure
- Common errors:
  - Invalid blueprint path
  - Location outside world bounds
  - Missing required parameters

## Related Skills

- `level-organizer` - Organize spawned actors into folders
- `screenshot` - Capture spawned scenes
- `blueprint-helper` - Create reusable blueprints from actors
