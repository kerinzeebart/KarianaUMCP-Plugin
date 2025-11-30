---
name: screenshot
description: Capture viewport screenshots and render high-quality images from Unreal Engine
version: 1.0.0
author: KarianaUMCP
dependencies:
  - unreal
  - pillow
---

# Screenshot Skill

Capture screenshots from Unreal Engine viewport with customizable resolution, format, and camera settings.

## Capabilities

- Capture current viewport
- Set custom resolution
- Configure output format (PNG, JPEG, WebP)
- Quality and compression settings
- Return as base64 or save to file
- Capture from specific camera actors

## Usage

### Basic Screenshot

```python
# Capture current viewport
take_screenshot()
```

### High Resolution

```python
take_screenshot(
    width=3840,
    height=2160,
    format="png"
)
```

### JPEG with Compression

```python
take_screenshot(
    format="jpeg",
    quality=85
)
```

### From Camera Actor

```python
take_screenshot(
    camera_actor="CineCameraActor_1",
    width=1920,
    height=1080
)
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| width | int | No | Image width (default: 1920) |
| height | int | No | Image height (default: 1080) |
| format | string | No | png, jpeg, webp (default: png) |
| quality | int | No | JPEG/WebP quality 1-100 (default: 90) |
| camera_actor | string | No | Camera actor name to capture from |
| save_path | string | No | File path to save (if not set, returns base64) |
| include_ui | bool | No | Include editor UI (default: false) |

## Response Format

```json
{
  "success": true,
  "image": "base64_encoded_data...",
  "format": "png",
  "width": 1920,
  "height": 1080,
  "size_bytes": 1234567
}
```

## Examples

### Thumbnail Generation

```python
# Generate small preview
take_screenshot(width=256, height=256, format="jpeg", quality=70)
```

### Product Shot

```python
# High-quality product render
take_screenshot(
    width=4096,
    height=4096,
    format="png",
    camera_actor="ProductCamera"
)
```

### Animation Frame Capture

```python
# Capture sequence frames
for frame in range(0, 120, 10):
    set_sequencer_time(frame / 30.0)
    take_screenshot(
        width=1920,
        height=1080,
        save_path=f"/tmp/frame_{frame:04d}.png"
    )
```

## Performance Notes

- PNG is lossless but larger files
- JPEG is fast but lossy
- High resolutions (4K+) may take several seconds
- Consider viewport size for real-time captures

## Error Handling

- Returns `{"success": false, "error": "..."}` on failure
- Common errors:
  - Camera actor not found
  - Invalid resolution
  - Disk write permission denied

## Related Skills

- `spawn-actor` - Set up scenes to capture
- `level-organizer` - Prepare scenes
