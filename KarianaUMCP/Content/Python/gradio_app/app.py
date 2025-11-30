"""
KarianaUMCP Gradio Web UI
=========================
6-tab dashboard for monitoring and control.

Tabs:
1. Status - Server health, connections, metrics
2. Tools - Test individual MCP tools
3. Skills - Browse and execute skills
4. Logs - Real-time UE logs and MCP traffic
5. Settings - ngrok config, port settings
6. Help - Documentation and examples
"""

import json
import socket
import time
import threading
from typing import Dict, Any, List, Optional

# Try to import gradio
try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    print("KarianaUMCP: Gradio not installed. Install with: pip install gradio")


def create_interface() -> Optional[Any]:
    """Create the Gradio interface"""
    if not GRADIO_AVAILABLE:
        return None

    with gr.Blocks(title="KarianaUMCP Dashboard", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# KarianaUMCP Dashboard")
        gr.Markdown("AI-powered Unreal Engine control via MCP")

        with gr.Tabs():
            # Tab 1: Status
            with gr.Tab("Status"):
                create_status_tab()

            # Tab 2: Tools
            with gr.Tab("Tools"):
                create_tools_tab()

            # Tab 3: Skills
            with gr.Tab("Skills"):
                create_skills_tab()

            # Tab 4: Logs
            with gr.Tab("Logs"):
                create_logs_tab()

            # Tab 5: Settings
            with gr.Tab("Settings"):
                create_settings_tab()

            # Tab 6: Help
            with gr.Tab("Help"):
                create_help_tab()

    return interface


def create_status_tab():
    """Create the Status tab"""
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Server Status")

            socket_status = gr.Textbox(
                label="Socket Server (9877)",
                value="Checking...",
                interactive=False
            )

            http_status = gr.Textbox(
                label="HTTP Proxy (8765)",
                value="Checking...",
                interactive=False
            )

            ngrok_status = gr.Textbox(
                label="ngrok Tunnel",
                value="Checking...",
                interactive=False
            )

            refresh_btn = gr.Button("Refresh Status")

        with gr.Column():
            gr.Markdown("### Connection Info")

            connection_info = gr.JSON(
                label="Server Info",
                value={}
            )

            tool_count = gr.Number(
                label="Available Tools",
                value=0,
                interactive=False
            )

    def check_status():
        """Check all service statuses"""
        results = {}

        # Check socket server
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 9877))
            sock.close()
            socket_stat = "Running" if result == 0 else "Not Running"
        except:
            socket_stat = "Error"

        # Check HTTP proxy
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 8765))
            sock.close()
            http_stat = "Running" if result == 0 else "Not Running"
        except:
            http_stat = "Error"

        # Check ngrok
        ngrok_stat = "Not Configured"
        try:
            from ngrok_proxy import get_proxy
            proxy = get_proxy()
            if proxy and proxy.ngrok_url:
                ngrok_stat = proxy.ngrok_url
        except:
            pass

        # Get server info
        info = {}
        count = 0
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', 9877))
            sock.send(b'{"type": "get_server_info"}\n')
            response = sock.recv(4096).decode('utf-8')
            sock.close()
            info = json.loads(response.strip())
        except:
            info = {"error": "Could not connect"}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', 9877))
            sock.send(b'{"type": "list_functions"}\n')
            response = sock.recv(8192).decode('utf-8')
            sock.close()
            data = json.loads(response.strip())
            count = data.get("count", 0)
        except:
            pass

        return socket_stat, http_stat, ngrok_stat, info, count

    refresh_btn.click(
        fn=check_status,
        outputs=[socket_status, http_status, ngrok_status, connection_info, tool_count]
    )


def create_tools_tab():
    """Create the Tools tab"""
    gr.Markdown("### Test MCP Tools")

    with gr.Row():
        tool_name = gr.Dropdown(
            label="Select Tool",
            choices=["ping", "list_functions", "list_actors", "execute_python", "capture_screenshot"],
            value="ping"
        )

        params_input = gr.Textbox(
            label="Parameters (JSON)",
            value="{}",
            lines=3
        )

    execute_btn = gr.Button("Execute Tool", variant="primary")

    result_output = gr.JSON(
        label="Result",
        value={}
    )

    def execute_tool(tool: str, params: str):
        """Execute an MCP tool"""
        try:
            params_dict = json.loads(params)
        except:
            params_dict = {}

        message = {"type": tool, **params_dict}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect(('localhost', 9877))
            sock.send((json.dumps(message) + '\n').encode('utf-8'))
            response = sock.recv(65536).decode('utf-8')
            sock.close()
            return json.loads(response.strip())
        except Exception as e:
            return {"error": str(e)}

    execute_btn.click(
        fn=execute_tool,
        inputs=[tool_name, params_input],
        outputs=[result_output]
    )


def create_skills_tab():
    """Create the Skills tab"""
    gr.Markdown("### Available Skills")

    skills_list = gr.Dataframe(
        headers=["Name", "Description", "Steps"],
        label="Skills",
        interactive=False
    )

    with gr.Row():
        skill_name_input = gr.Textbox(
            label="Skill Name",
            placeholder="organize_level"
        )

        skill_params = gr.Textbox(
            label="Parameters (JSON)",
            value="{}",
            lines=2
        )

    execute_skill_btn = gr.Button("Execute Skill", variant="primary")

    skill_result = gr.JSON(
        label="Skill Result",
        value={}
    )

    def load_skills():
        """Load available skills"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', 9877))
            sock.send(b'{"type": "list_skills"}\n')
            response = sock.recv(4096).decode('utf-8')
            sock.close()

            data = json.loads(response.strip())
            skills = data.get("skills", [])

            return [[s.get("name"), s.get("description"), s.get("steps")] for s in skills]
        except:
            return []

    def execute_skill(name: str, params: str):
        """Execute a skill"""
        try:
            params_dict = json.loads(params)
        except:
            params_dict = {}

        message = {"type": "execute_skill", "skill_name": name, "parameters": params_dict}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(60)
            sock.connect(('localhost', 9877))
            sock.send((json.dumps(message) + '\n').encode('utf-8'))
            response = sock.recv(65536).decode('utf-8')
            sock.close()
            return json.loads(response.strip())
        except Exception as e:
            return {"error": str(e)}

    skills_list.value = load_skills()

    execute_skill_btn.click(
        fn=execute_skill,
        inputs=[skill_name_input, skill_params],
        outputs=[skill_result]
    )


def create_logs_tab():
    """Create the Logs tab"""
    gr.Markdown("### Unreal Engine Logs")

    with gr.Row():
        lines_input = gr.Slider(
            minimum=10,
            maximum=500,
            value=100,
            step=10,
            label="Lines to fetch"
        )

        category_filter = gr.Textbox(
            label="Category filter (optional)",
            placeholder="LogPython"
        )

    fetch_logs_btn = gr.Button("Fetch Logs")

    logs_output = gr.Textbox(
        label="Logs",
        lines=20,
        max_lines=50,
        interactive=False
    )

    def fetch_logs(lines: int, category: str):
        """Fetch UE logs"""
        message = {
            "type": "get_ue_logs",
            "lines": int(lines),
            "category": category if category else ""
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect(('localhost', 9877))
            sock.send((json.dumps(message) + '\n').encode('utf-8'))
            response = sock.recv(65536).decode('utf-8')
            sock.close()

            data = json.loads(response.strip())
            logs = data.get("logs", [])
            return "\n".join(logs) if logs else "No logs found"
        except Exception as e:
            return f"Error: {e}"

    fetch_logs_btn.click(
        fn=fetch_logs,
        inputs=[lines_input, category_filter],
        outputs=[logs_output]
    )


def create_settings_tab():
    """Create the Settings tab"""
    gr.Markdown("### Server Settings")

    with gr.Row():
        with gr.Column():
            gr.Markdown("#### Ports")

            socket_port = gr.Number(
                label="Socket Port",
                value=9877,
                interactive=False
            )

            http_port = gr.Number(
                label="HTTP Port",
                value=8765,
                interactive=False
            )

        with gr.Column():
            gr.Markdown("#### ngrok")

            ngrok_token = gr.Textbox(
                label="ngrok Auth Token",
                type="password",
                placeholder="Enter your ngrok token"
            )

            start_ngrok_btn = gr.Button("Start ngrok Tunnel")
            stop_ngrok_btn = gr.Button("Stop ngrok Tunnel")

            ngrok_url_display = gr.Textbox(
                label="ngrok URL",
                interactive=False
            )

    def start_ngrok(token: str):
        """Start ngrok tunnel"""
        try:
            from ngrok_proxy import start_proxy, get_proxy
            proxy = start_proxy(start_ngrok=True, ngrok_token=token if token else None)
            if proxy and proxy.ngrok_url:
                return proxy.ngrok_url
            return "Failed to start"
        except Exception as e:
            return f"Error: {e}"

    def stop_ngrok():
        """Stop ngrok tunnel"""
        try:
            from ngrok_proxy import get_proxy
            proxy = get_proxy()
            if proxy:
                proxy.stop_ngrok()
                return "Stopped"
            return "Not running"
        except Exception as e:
            return f"Error: {e}"

    start_ngrok_btn.click(
        fn=start_ngrok,
        inputs=[ngrok_token],
        outputs=[ngrok_url_display]
    )

    stop_ngrok_btn.click(
        fn=stop_ngrok,
        outputs=[ngrok_url_display]
    )


def create_help_tab():
    """Create the Help tab"""
    gr.Markdown("""
    ### KarianaUMCP Help

    #### Quick Start

    1. **Verify Connection**: Go to the Status tab and click "Refresh Status"
    2. **Test a Tool**: Go to the Tools tab, select "ping", and click "Execute Tool"
    3. **List Actors**: Select "list_actors" to see all actors in your level

    #### Common Tools

    | Tool | Description |
    |------|-------------|
    | `ping` | Test server connectivity |
    | `list_functions` | List all available tools |
    | `list_actors` | List all actors in the level |
    | `spawn_actor` | Spawn a new actor |
    | `execute_python` | Run Python code in Unreal |
    | `capture_screenshot` | Take a viewport screenshot |

    #### Using with Claude Desktop

    Add this to your Claude Desktop config:

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

    #### Skills

    Skills are pre-defined workflows that execute multiple tools in sequence.
    Available skills:
    - `organize_level` - Organize actors into folders
    - `create_lighting_setup` - Create three-point lighting

    #### Troubleshooting

    **Socket server not running:**
    - Restart Unreal Engine
    - Check Python Script Plugin is enabled
    - Run `installer.setup()` in Unreal Python console

    **ngrok not starting:**
    - Install pyngrok: `pip install pyngrok`
    - Enter your ngrok auth token in Settings

    **Tools failing:**
    - Check Unreal Engine is running
    - Verify the actor/asset exists
    - Check Logs tab for error details
    """)


def launch_ui(port: int = 7860, share: bool = False):
    """Launch the Gradio UI"""
    if not GRADIO_AVAILABLE:
        print("KarianaUMCP: Cannot launch UI - Gradio not installed")
        return None

    interface = create_interface()
    if interface:
        interface.launch(
            server_port=port,
            share=share,
            prevent_thread_lock=True
        )
        print(f"KarianaUMCP: Gradio UI running at http://localhost:{port}")
        return interface
    return None


# Export
__all__ = ['create_interface', 'launch_ui', 'GRADIO_AVAILABLE']
