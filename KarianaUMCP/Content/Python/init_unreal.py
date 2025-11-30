"""
KarianaUMCP - init_unreal.py
=============================
This script auto-runs when Unreal Engine loads the plugin.
No configuration required - just install the plugin and restart Unreal.

The PIN will appear in the Output Log (Window > Output Log).
"""

import sys
import os
import threading

# Initialize logging early
from logger import get_logger
logger = get_logger("init")


def _start_kariana_services():
    """Start KarianaUMCP services in background thread"""

    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Add to Python path if not already there
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    try:
        # Import and start the socket server
        from socket_server import start_server
        server = start_server(host="0.0.0.0", port=9877, require_auth=False)

        if server and server.instance_manager:
            pin = server.instance_manager.pin
            port = server.port

            # Start HTTP proxy for Claude Desktop
            http_port = None
            try:
                from ngrok_proxy import start_proxy
                proxy = start_proxy(http_port=8765, socket_port=port)
                http_port = 8765
            except Exception as e:
                logger.warning(f"HTTP proxy not started: {e}")

            # Display prominent banner
            _display_banner(pin, port, http_port)

    except Exception as e:
        logger.exception(f"Failed to start services: {e}")


def _display_banner(pin: str, port: int, http_port: int = None):
    """Display connection information in Output Log"""
    try:
        import unreal

        # Yellow warning messages are most visible
        unreal.log_warning("")
        unreal.log_warning("=" * 60)
        unreal.log_warning("  KARIANA UMCP - AI Virtual Production Control")
        unreal.log_warning("=" * 60)
        unreal.log_warning("")
        unreal.log_warning(f"  CONNECTION PIN:  {pin}")
        unreal.log_warning(f"  SOCKET PORT:     {port}")
        if http_port:
            unreal.log_warning(f"  HTTP PORT:       {http_port}")
        unreal.log_warning("")
        unreal.log_warning("  Dashboard: https://barlowski-karianaumcp.hf.space")
        unreal.log_warning("")
        unreal.log_warning("  For ngrok: ngrok tcp 9877")
        unreal.log_warning("")
        unreal.log_warning("=" * 60)
        unreal.log_warning("")

    except ImportError:
        # Fallback for non-Unreal environment - use logger instead of print
        logger.info("=" * 60)
        logger.info("  KARIANA UMCP - CONNECTION INFO")
        logger.info(f"  PIN:     {pin}")
        logger.info(f"  Socket:  localhost:{port}")
        logger.info(f"  HTTP:    localhost:{http_port or 'N/A'}")
        logger.info("  Dashboard: https://barlowski-karianaumcp.hf.space")
        logger.info("=" * 60)


# Set UE_PROJECT_DIR for safe access to project path in other modules
def _set_project_dir():
    """Set project directory env var safely during Unreal init"""
    try:
        import unreal
        project_dir = unreal.Paths.project_dir()
        os.environ["UE_PROJECT_DIR"] = project_dir
        logger.info(f"Project dir set to {project_dir}")
    except Exception as e:
        logger.warning(f"Could not set project dir: {e}")


def _init_main_thread_executor():
    """Initialize main thread executor while on main thread"""
    try:
        # Import here to trigger registration on main thread
        from main_thread_executor import _register_tick_callback
        if _register_tick_callback():
            logger.info("Main thread executor ready")
        else:
            logger.warning("Main thread executor not available")
    except Exception as e:
        logger.warning(f"Could not init main thread executor: {e}")


# Auto-start when this module is imported by Unreal
logger.info("Initializing...")
_set_project_dir()  # Set early while Unreal is in stable state
_init_main_thread_executor()  # Register tick callback on main thread

# Start services in background thread to not block editor startup
thread = threading.Thread(target=_start_kariana_services, daemon=True)
thread.start()

logger.info("Services starting in background...")
