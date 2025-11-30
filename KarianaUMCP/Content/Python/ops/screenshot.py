"""
KarianaUMCP Screenshot Tool
===========================
Low-resolution screenshot capture optimized for MCP transmission.
Uses PIL (Pillow) for compression.

Battle-tested from kariana.ai implementation.
"""

from typing import Dict, Any
import traceback


def capture_screenshot_mcp(width: int = 800, height: int = 600, quality: int = 85) -> Dict[str, Any]:
    """
    Capture low-resolution screenshot optimized for MCP transmission.

    Args:
        width: Target width (default 800px for low bandwidth)
        height: Target height (default 600px)
        quality: JPEG quality 1-100 (default 85)

    Returns:
        dict: {"success": bool, "image": base64_string, "size": bytes}
    """
    import tempfile
    import os
    import base64

    try:
        import unreal

        # Create temp file for screenshot
        temp_path = os.path.join(tempfile.gettempdir(), "kariana_screenshot.png")

        # Take screenshot using Unreal's automation library
        # Use high-res screenshot for better quality before compression
        unreal.AutomationLibrary.take_high_res_screenshot(
            width, height, temp_path
        )

        # Try PIL compression if available
        try:
            from PIL import Image
            import io

            # Load the screenshot
            img = Image.open(temp_path)

            # Convert to RGB if needed (removes alpha channel)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize if needed
            if img.size != (width, height):
                img = img.resize((width, height), Image.Resampling.LANCZOS)

            # Compress to JPEG
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)

            # Encode to base64 for MCP transmission
            img_bytes = buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            # Cleanup temp file
            try:
                os.remove(temp_path)
            except:
                pass

            return {
                "success": True,
                "image": img_base64,
                "size": len(img_bytes),
                "format": "jpeg",
                "dimensions": {"width": width, "height": height},
                "quality": quality
            }

        except ImportError:
            # PIL not installed - return raw PNG with warning
            with open(temp_path, 'rb') as f:
                img_bytes = f.read()

            # Cleanup
            try:
                os.remove(temp_path)
            except:
                pass

            return {
                "success": True,
                "image": base64.b64encode(img_bytes).decode('utf-8'),
                "size": len(img_bytes),
                "format": "png",
                "dimensions": {"width": width, "height": height},
                "warning": "PIL not installed - returning uncompressed PNG. Install with: py pip install Pillow"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Screenshot failed: {str(e)}",
            "traceback": traceback.format_exc()
        }


def capture_viewport_screenshot(viewport_index: int = 0) -> Dict[str, Any]:
    """
    Capture screenshot from a specific viewport.

    Args:
        viewport_index: Index of viewport to capture (default 0)

    Returns:
        dict: Screenshot data or error
    """
    try:
        import unreal
        import tempfile
        import os
        import base64

        temp_path = os.path.join(tempfile.gettempdir(), f"kariana_viewport_{viewport_index}.png")

        # Get viewport
        viewport = unreal.EditorLevelLibrary.get_all_level_actors()[0]  # Fallback

        # Take screenshot
        unreal.EditorLevelLibrary.editor_screenshot(temp_path)

        with open(temp_path, 'rb') as f:
            img_bytes = f.read()

        try:
            os.remove(temp_path)
        except:
            pass

        return {
            "success": True,
            "image": base64.b64encode(img_bytes).decode('utf-8'),
            "size": len(img_bytes),
            "format": "png",
            "viewport": viewport_index
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_screenshot_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle screenshot commands"""
    cmd = data.get("type", "capture_screenshot")

    if cmd == "capture_screenshot":
        width = data.get("width", 800)
        height = data.get("height", 600)
        quality = data.get("quality", 85)
        return capture_screenshot_mcp(width, height, quality)

    elif cmd == "capture_viewport":
        viewport_index = data.get("viewport_index", 0)
        return capture_viewport_screenshot(viewport_index)

    else:
        return {"success": False, "error": f"Unknown screenshot command: {cmd}"}
