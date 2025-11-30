"""
KarianaUMCP System Operations
=============================
System commands and utilities.
CRITICAL: This is the fixed ue_logs implementation from kariana.ai.

Supports:
- console_command
- get_ue_logs (FIXED VERSION)
- get_engine_info
- get_project_info
"""

from typing import Dict, Any, List
import traceback


def handle_system_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Route system commands to appropriate handlers"""
    cmd = data.get("type", "")

    handlers = {
        "console_command": execute_console_command,
        "get_ue_logs": get_ue_logs,
        "get_engine_info": get_engine_info,
        "get_project_info": get_project_info,
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
        return {"success": False, "error": f"Unknown system command: {cmd}"}


def execute_console_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an Unreal console command"""
    import unreal

    command = data.get("command", "")

    if not command:
        return {"success": False, "error": "command is required"}

    try:
        # Execute the console command
        unreal.SystemLibrary.execute_console_command(None, command)

        return {
            "success": True,
            "command": command,
            "message": "Command executed successfully"
        }

    except Exception as e:
        return {"success": False, "error": f"Command failed: {e}"}


def get_ue_logs(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get Unreal Engine logs.

    FIXED VERSION - Uses environment variable instead of Unreal API to avoid crashes.

    Args:
        lines: Number of lines to return (default 100)
        category: Filter by log category (optional)
        severity: Filter by severity level (optional)
    """
    import os

    lines = data.get("lines", 100)
    category = data.get("category", "")
    severity = data.get("severity", "")

    try:
        log_entries = []

        # Get project directory from environment (set by init_unreal.py)
        # This avoids calling Unreal API which can crash during certain engine states
        project_dir = os.environ.get("UE_PROJECT_DIR", "")

        if not project_dir:
            # Fallback: derive from plugin location
            plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # Plugin is at: Project/Plugins/KarianaUMCP/Content/Python/ops
            # So project is 5 levels up
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(plugin_dir))))

        log_dir = os.path.join(project_dir, "Saved", "Logs")

        # Find the most recent log file
        log_files = []
        if os.path.exists(log_dir):
            for f in os.listdir(log_dir):
                if f.endswith(".log"):
                    log_files.append(os.path.join(log_dir, f))

        if log_files:
            # Get the most recently modified log file
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            current_log = log_files[0]

            try:
                with open(current_log, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read last N lines efficiently
                    all_lines = f.readlines()
                    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

                    for line in recent_lines:
                        line = line.strip()
                        if not line:
                            continue

                        # Apply filters
                        if category and category.lower() not in line.lower():
                            continue
                        if severity:
                            severity_lower = severity.lower()
                            if severity_lower == "error" and "error" not in line.lower():
                                continue
                            elif severity_lower == "warning" and "warning" not in line.lower():
                                continue

                        log_entries.append(line)

                return {
                    "success": True,
                    "logs": log_entries,
                    "count": len(log_entries),
                    "source": "log_file",
                    "file": current_log
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to read log file: {e}"
                }

        # Fallback: Return minimal log info
        return {
            "success": True,
            "logs": [],
            "count": 0,
            "message": "No log files found. Logs may be written to console."
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get logs: {e}",
            "traceback": traceback.format_exc()
        }


def get_engine_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get Unreal Engine information"""
    import unreal
    import os

    try:
        # Get project name from directory or .uproject file
        project_dir = str(unreal.Paths.project_dir())
        project_name = os.path.basename(project_dir.rstrip('/\\'))

        # Try to find .uproject file for more accurate name
        for f in os.listdir(project_dir):
            if f.endswith('.uproject'):
                project_name = f.replace('.uproject', '')
                break

        return {
            "success": True,
            "engine_version": unreal.SystemLibrary.get_engine_version(),
            "project_directory": project_dir,
            "project_name": project_name,
            "is_editor": unreal.SystemLibrary.is_editor(),
            "platform": str(unreal.SystemLibrary.get_platform_user_name())
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_project_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get project information"""
    import unreal
    import os

    try:
        project_dir = str(unreal.Paths.project_dir())

        # Get project file
        project_files = [f for f in os.listdir(project_dir) if f.endswith('.uproject')]
        project_file = project_files[0] if project_files else None

        # Get plugin list
        plugins_dir = os.path.join(project_dir, "Plugins")
        plugins = []
        if os.path.exists(plugins_dir):
            for item in os.listdir(plugins_dir):
                plugin_path = os.path.join(plugins_dir, item)
                if os.path.isdir(plugin_path):
                    uplugin_files = [f for f in os.listdir(plugin_path) if f.endswith('.uplugin')]
                    if uplugin_files:
                        plugins.append(item)

        return {
            "success": True,
            "project_name": str(unreal.Paths.project_name()),
            "project_directory": project_dir,
            "project_file": project_file,
            "plugins": plugins,
            "plugin_count": len(plugins),
            "content_directory": str(unreal.Paths.project_content_dir()),
            "saved_directory": str(unreal.Paths.project_saved_dir())
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
