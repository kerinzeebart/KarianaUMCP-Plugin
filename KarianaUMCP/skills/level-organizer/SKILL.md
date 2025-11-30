---
name: level-organizer
description: Organize actors in Unreal Engine World Outliner with smart folder hierarchies
version: 1.0.0
author: KarianaUMCP
dependencies:
  - unreal
---

# Level Organizer Skill

Intelligently organize actors in the Unreal Engine World Outliner with automated folder hierarchies, batch renaming, and smart categorization.

## Capabilities

- Create folder hierarchies in World Outliner
- Move actors to folders
- Batch rename actors
- Auto-categorize by actor type
- Discover project structure
- Apply naming conventions

## Usage

### Create Folder

```python
create_outliner_folder(
    folder_path="Environment/Props"
)
```

### Move Actor to Folder

```python
move_actor_to_folder(
    actor_name="Cube_1",
    folder_path="Environment/Props"
)
```

### Batch Move by Pattern

```python
organize_actors_by_pattern(
    pattern="SM_*",
    folder_path="Environment/StaticMeshes"
)
```

### Auto-Organize Level

```python
auto_organize_level()
```

## Parameters

### create_outliner_folder

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| folder_path | string | Yes | Folder path (use / for hierarchy) |

### move_actor_to_folder

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| actor_name | string | Yes | Actor name or pattern |
| folder_path | string | Yes | Destination folder |

### organize_actors_by_pattern

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| pattern | string | Yes | Glob pattern (*, ?) |
| folder_path | string | Yes | Destination folder |

### rename_actors

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| pattern | string | Yes | Actors matching pattern |
| new_name | string | Yes | New name template |
| start_index | int | No | Starting number (default: 1) |

## Examples

### Standard Project Organization

```python
# Create standard folders
create_outliner_folder("Environment")
create_outliner_folder("Environment/Lighting")
create_outliner_folder("Environment/Props")
create_outliner_folder("Environment/Architecture")
create_outliner_folder("Gameplay")
create_outliner_folder("Gameplay/Characters")
create_outliner_folder("Gameplay/Interactables")
create_outliner_folder("VFX")
create_outliner_folder("Audio")
create_outliner_folder("Cameras")
```

### Organize by Actor Type

```python
# Move all lights
organize_actors_by_pattern(
    pattern="*Light*",
    folder_path="Environment/Lighting"
)

# Move all cameras
organize_actors_by_pattern(
    pattern="*Camera*",
    folder_path="Cameras"
)

# Move all audio
organize_actors_by_pattern(
    pattern="*Audio*",
    folder_path="Audio"
)
```

### Batch Rename

```python
# Rename scattered cubes to organized names
rename_actors(
    pattern="Cube_*",
    new_name="Prop_Box",
    start_index=1
)
# Results: Prop_Box_001, Prop_Box_002, etc.
```

### Auto-Organization

```python
# Let the system analyze and organize
result = auto_organize_level()
# Returns summary of changes made
```

## Auto-Organization Categories

When using `auto_organize_level()`, actors are categorized by type:

| Actor Type | Default Folder |
|------------|----------------|
| DirectionalLight, PointLight, SpotLight, RectLight | Environment/Lighting |
| StaticMeshActor | Environment/Props |
| SkeletalMeshActor | Gameplay/Characters |
| CameraActor, CineCameraActor | Cameras |
| AudioComponent, AmbientSound | Audio |
| PlayerStart, Trigger* | Gameplay |
| Emitter, NiagaraActor | VFX |
| PostProcessVolume, LightmassImportanceVolume | Technical |

## Response Format

```json
{
  "success": true,
  "actions": [
    {"type": "folder_created", "path": "Environment/Props"},
    {"type": "actor_moved", "actor": "Cube_1", "to": "Environment/Props"},
    {"type": "actor_renamed", "old": "Cube_2", "new": "Prop_Box_001"}
  ],
  "summary": {
    "folders_created": 5,
    "actors_moved": 23,
    "actors_renamed": 10
  }
}
```

## Best Practices

1. **Establish Convention Early** - Set up folders before heavy level design
2. **Use Consistent Naming** - Prefix actors by type (SM_, BP_, VFX_)
3. **Regular Cleanup** - Periodically run organization on messy levels
4. **Project-Specific Folders** - Adapt structure to your game's needs
5. **Backup Before Bulk Changes** - Save level before major reorganization

## Discovery-First Approach

This skill dynamically discovers project structure rather than assuming paths:

```python
# Discover current level
level_info = discover_current_level()

# Build paths dynamically
move_actor_to_folder(
    actor_name="Cube_1",
    folder_path=f"{level_info['name']}/Props"
)
```

## Error Handling

- Returns `{"success": false, "error": "..."}` on failure
- Common errors:
  - Actor not found
  - Invalid folder path characters
  - Permission denied (locked actors)

## Related Skills

- `spawn-actor` - Create actors to organize
- `blueprint-helper` - Create Blueprints from organized actors
