# KarianaUMCP - Unified MCP Plugin for Unreal Engine

AI-powered Unreal Engine control through the Model Context Protocol (MCP).

## Features

- **52+ Battle-Tested Tools** - Verified 95%+ success rate
- **Skills System** - Guided workflows with step-by-step execution
- **Blueprint Intelligence** - Auto-wiring and pin discovery
- **Gradio Web UI** - Monitor and control via browser
- **ngrok Integration** - Remote access for Claude Desktop
- **One-Click Installer** - Automatic setup

## Quick Start

### 1. Install the Plugin

Copy the `KarianaUMCP` folder to your project's `Plugins` directory.

### 2. Run the Installer

In Unreal's Python console:

```python
import sys
sys.path.append('/path/to/KarianaUMCP/Content/Python')
import installer
installer.install_and_setup()
```

### 3. Configure Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "kariana": {
      "command": "node",
      "args": ["/path/to/kariana-mcp-bridge.js"],
      "env": {
        "KARIANA_URL": "YOUR_NGROK_URL"
      }
    }
  }
}
```

### 4. Test

In Claude Desktop, try: "List all actors in my Unreal level"

## Core Tools

### Actor Operations
- `spawn_actor` - Spawn actors in the level
- `delete_actor` - Delete actors
- `list_actors` - List all actors
- `set_actor_location` - Move actors
- `set_actor_rotation` - Rotate actors
- `set_actor_scale` - Scale actors

### Blueprint Operations
- `create_blueprint` - Create new Blueprints
- `add_blueprint_component` - Add components
- `compile_blueprint` - Compile Blueprints
- `auto_wire_blueprint` - Auto-connect nodes

### Asset Operations
- `import_asset` - Import external files
- `list_assets` - Browse content
- `create_material` - Create materials

### System Operations
- `execute_python` - Run Python code
- `capture_screenshot` - Take screenshots
- `get_ue_logs` - View engine logs

## Skills

Pre-defined workflows:

- `organize_level` - Organize actors into folders
- `create_lighting_setup` - Create three-point lighting

## Gradio Dashboard

Access at `http://localhost:7860` when running:

- **Status Tab** - Server health monitoring
- **Tools Tab** - Test individual tools
- **Skills Tab** - Execute workflows
- **Logs Tab** - View Unreal logs
- **Settings Tab** - Configure ngrok
- **Help Tab** - Documentation

## Architecture

```
Claude Desktop
      ↓
  MCP Protocol
      ↓
kariana-mcp-bridge.js
      ↓
  HTTP (ngrok)
      ↓
ngrok_proxy.py
      ↓
socket_server.py (port 9877)
      ↓
Unreal Engine Python
```

## Requirements

- Unreal Engine 5.4+
- Python Script Plugin (enabled)
- Node.js 18+ (for MCP bridge)

## Troubleshooting

### Socket server not starting

1. Restart Unreal Engine
2. Check Python Script Plugin is enabled
3. Verify port 9877 is available

### ngrok not connecting

1. Install pyngrok: `pip install pyngrok`
2. Enter your ngrok auth token
3. Check internet connectivity

### Tools returning errors

1. Check Unreal Engine is running
2. Verify asset/actor paths
3. View Logs tab for details

## License

MIT License

## Credits

Created by Kariana.ai
