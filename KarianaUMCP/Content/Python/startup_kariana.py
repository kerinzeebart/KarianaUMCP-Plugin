"""
KarianaUMCP Startup Script
==========================
This script is designed to be run at Unreal Engine startup.

HOW TO USE:
1. Open Unreal Editor
2. Go to: Edit > Project Settings > Plugins > Python
3. Under "Startup Scripts", add:
   /KarianaUMCP/Python/startup_kariana.py
4. Restart Unreal Editor

The PIN will appear in the Output Log.
"""

import sys
import os

def start_kariana():
    """Start KarianaUMCP services"""
    print("=" * 60)
    print("  KarianaUMCP: Initializing...")
    print("=" * 60)

    try:
        # Get the directory containing this script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Add to Python path if not already there
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            print(f"KarianaUMCP: Added to Python path: {script_dir}")

        # Import and start the socket server
        from socket_server import start_server
        server = start_server(host="0.0.0.0", port=9877, require_auth=False)

        if server and server.instance_manager:
            pin = server.instance_manager.pin
            port = server.port

            # Start HTTP proxy
            http_port = None
            try:
                from ngrok_proxy import start_proxy
                proxy = start_proxy(http_port=8765, socket_port=port)
                http_port = 8765
            except Exception as e:
                print(f"KarianaUMCP: HTTP proxy not started - {e}")

            # Display prominent banner
            _display_banner(pin, port, http_port)

            print("KarianaUMCP: All services started successfully!")
            return True
        else:
            print("KarianaUMCP: Server started but no instance manager")
            return False

    except Exception as e:
        import traceback
        print(f"KarianaUMCP: Failed to start - {e}")
        traceback.print_exc()
        return False


def _display_banner(pin: str, port: int, http_port: int = None):
    """Display connection information banner"""
    try:
        import unreal

        # Use log_warning for visibility (appears in yellow)
        unreal.log_warning("=" * 64)
        unreal.log_warning("  KARIANA UMCP - AI Virtual Production Control")
        unreal.log_warning("=" * 64)
        unreal.log_warning(f"  CONNECTION PIN: {pin}")
        unreal.log_warning(f"  SOCKET PORT:    {port}")
        if http_port:
            unreal.log_warning(f"  HTTP PORT:      {http_port}")
        unreal.log_warning("=" * 64)
        unreal.log_warning("  Dashboard: https://barlowski-karianaumcp.hf.space")
        unreal.log_warning("=" * 64)

        # Also print full banner to regular log
        unreal.log(f"""
============================================================
  KARIANA UMCP - CONNECTION INFO
============================================================

  PIN:         {pin}
  Socket:      localhost:{port}
  HTTP:        localhost:{http_port or 'N/A'}

  FOR REMOTE ACCESS:
  1. Install ngrok: https://ngrok.com
  2. Run: ngrok tcp {port}
  3. Enter ngrok URL at: https://barlowski-karianaumcp.hf.space

============================================================
""")

    except ImportError:
        # Not in Unreal, just print
        print(f"""
============================================================
  KARIANA UMCP - CONNECTION INFO
============================================================

  PIN:         {pin}
  Socket:      localhost:{port}
  HTTP:        localhost:{http_port or 'N/A'}

============================================================
""")


# Auto-run when this script is executed
if __name__ == "__main__" or __name__ == "startup_kariana":
    start_kariana()
else:
    # When imported, also try to start
    try:
        import unreal
        start_kariana()
    except ImportError:
        pass
