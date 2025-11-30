# KarianaUMCP - Unified MCP Plugin for Unreal Engine
# Version 1.0.1

"""
KarianaUMCP provides AI-powered control of Unreal Engine through:
- 52+ battle-tested MCP tools
- Skills system with guided workflows
- Blueprint Intelligence with auto-wiring
- Gradio Web UI for monitoring
- ngrok remote access for Claude Desktop

Auto-starts all services when Unreal Engine loads.
PIN is displayed prominently in Output Log for easy connection.
"""

__version__ = "1.0.1"
__author__ = "Kariana.ai"

# Store global references
_server = None
_pin = None
_port = None
_http_port = None
_ngrok_url = None


def get_connection_info():
    """Get current connection PIN and port"""
    return {"pin": _pin, "port": _port}


def _auto_start():
    """Initialize all KarianaUMCP services with proper PIN display"""
    global _server, _pin, _port, _http_port, _ngrok_url
    import threading
    import sys
    import os

    def start_services():
        global _server, _pin, _port, _http_port, _ngrok_url
        try:
            # Add plugin path
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)

            # Use start_server() for proper initialization with PIN
            from socket_server import start_server, get_server
            _server = start_server(host="0.0.0.0", port=9877, require_auth=False)

            # Get PIN from instance manager
            if _server and _server.instance_manager:
                _pin = _server.instance_manager.pin
                _port = _server.port

            # Start HTTP proxy for Claude Desktop/ngrok connectivity
            try:
                from ngrok_proxy import start_proxy
                proxy = start_proxy(http_port=8765, socket_port=_port)
                _http_port = 8765
                print("KarianaUMCP: HTTP proxy started on port 8765")
            except Exception as proxy_err:
                print(f"KarianaUMCP: HTTP proxy not started - {proxy_err}")
                _http_port = None

            # Display prominent PIN notification
            _display_pin_banner(_pin, _port, _http_port)

            print("KarianaUMCP: All services started successfully")

        except Exception as e:
            import traceback
            print(f"KarianaUMCP: Failed to start services - {e}")
            traceback.print_exc()

    # Start in background thread to not block Unreal
    thread = threading.Thread(target=start_services, daemon=True)
    thread.start()


def _display_pin_banner(pin: str, port: int, http_port: int = None):
    """Display very prominent PIN banner in Output Log"""
    http_section = ""
    if http_port:
        http_section = f"""
║   Claude Desktop Connection:                                 ║
║   1. Run: ngrok http {http_port}                             ║
║   2. Add to claude_desktop_config.json:                      ║
║      "kariana": {{"url": "YOUR_NGROK_URL"}}                   ║
║                                                              ║"""

    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   KARIANA UMCP - AI Virtual Production Control Ready!        ║
║                                                              ║
║   ┌────────────────────────────────────────────────────┐     ║
║   │                                                    │     ║
║   │           CONNECTION PIN:  {pin}                   │     ║
║   │                                                    │     ║
║   │           SOCKET PORT: {port}                      │     ║
║   │           HTTP PORT:   {http_port or 'N/A'}                      │     ║
║   │                                                    │     ║
║   └────────────────────────────────────────────────────┘     ║
║                                                              ║
║   Web Dashboard: https://barlowski-karianaumcp.hf.space      ║
║                                                              ║
║   For Remote Access (ngrok):                                 ║
║   - Socket: ngrok tcp {port}   (for direct connections)      ║
║   - HTTP:   ngrok http {http_port or 8765}  (for Claude Desktop)        ║
║                                                              ║{http_section}
╚══════════════════════════════════════════════════════════════╝
"""
    try:
        import unreal
        # Use multiple log methods for visibility
        unreal.log_warning("=" * 64)
        unreal.log_warning(f"  KARIANA UMCP - CONNECTION PIN: {pin}")
        unreal.log_warning(f"  SOCKET PORT: {port} | HTTP PORT: {http_port or 'N/A'}")
        unreal.log_warning("=" * 64)
        unreal.log(banner)
    except ImportError:
        print(banner)


# Only auto-start if running in Unreal
try:
    import unreal
    _auto_start()
except ImportError:
    pass  # Not running in Unreal, skip auto-start
