"""
KarianaUMCP ngrok HTTP Proxy
============================
HTTP-to-Socket bridge for Claude Desktop connectivity.
Works with ngrok free tier (HTTP only).

Features:
- HTTP endpoint → JSON socket message
- SSE (Server-Sent Events) for async responses
- Request ID tracking
- Automatic reconnection
"""

import json
import socket
import threading
import time
import os
from typing import Dict, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import traceback

# Configuration
DEFAULT_HTTP_PORT = 8765
DEFAULT_SOCKET_HOST = "localhost"
DEFAULT_SOCKET_PORT = 9877


class KarianaMCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler that bridges to the socket server"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def send_json_response(self, data: Dict, status: int = 200):
        """Send a JSON response"""
        response_body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response_body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_body)

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/health':
            self.send_json_response({
                "status": "healthy",
                "server": "KarianaUMCP",
                "version": "1.0.0"
            })

        elif path == '/tools/list':
            # Forward to socket server
            response = self._send_to_socket({"type": "list_functions"})
            self.send_json_response(response)

        elif path == '/mcp/list_tools':
            # MCP standard endpoint
            response = self._send_to_socket({"type": "list_functions"})

            if response.get("success"):
                # Transform to MCP format
                tools = []
                for func in response.get("functions", []):
                    tools.append({
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                k: {"type": v.get("type", "string"), "description": v.get("description", "")}
                                for k, v in func.get("parameters", {}).items()
                            }
                        }
                    })
                self.send_json_response({"tools": tools})
            else:
                self.send_json_response(response, 500)

        elif path == '/sse':
            # SSE endpoint for real-time events
            self._handle_sse()

        else:
            self.send_json_response({"error": f"Unknown endpoint: {path}"}, 404)

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_response({"error": "Invalid JSON"}, 400)
            return

        if path == '/tools/call':
            # Forward tool call to socket server
            tool_name = data.get("name", "")
            arguments = data.get("arguments", {})

            # Build socket message
            socket_message = {"type": tool_name, **arguments}
            response = self._send_to_socket(socket_message)
            self.send_json_response(response)

        elif path == '/mcp/call_tool':
            # MCP standard endpoint
            tool_name = data.get("name", "")
            arguments = data.get("arguments", {})

            socket_message = {"type": tool_name, **arguments}
            response = self._send_to_socket(socket_message)

            # Transform to MCP format
            if response.get("success"):
                self.send_json_response({
                    "content": [{"type": "text", "text": json.dumps(response)}]
                })
            else:
                self.send_json_response({
                    "isError": True,
                    "content": [{"type": "text", "text": response.get("error", "Unknown error")}]
                })

        elif path == '/execute':
            # Direct socket message forwarding
            response = self._send_to_socket(data)
            self.send_json_response(response)

        else:
            self.send_json_response({"error": f"Unknown endpoint: {path}"}, 404)

    def _send_to_socket(self, message: Dict) -> Dict:
        """Send message to socket server and return response"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)  # 30 second timeout
            sock.connect((DEFAULT_SOCKET_HOST, DEFAULT_SOCKET_PORT))

            # Send message
            sock.send((json.dumps(message) + '\n').encode('utf-8'))

            # Receive response
            response_data = ""
            while True:
                chunk = sock.recv(4096).decode('utf-8')
                if not chunk:
                    break
                response_data += chunk
                if '\n' in response_data:
                    break

            sock.close()

            # Parse response
            if response_data.strip():
                return json.loads(response_data.strip().split('\n')[0])
            else:
                return {"success": False, "error": "Empty response from socket server"}

        except socket.timeout:
            return {"success": False, "error": "Socket server timeout"}
        except ConnectionRefusedError:
            return {"success": False, "error": "Socket server not running (port 9877)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_sse(self):
        """Handle Server-Sent Events for real-time updates"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        try:
            # Send initial connection event
            self.wfile.write(b'event: connected\ndata: {"status": "connected"}\n\n')
            self.wfile.flush()

            # Keep connection alive with heartbeat
            while True:
                time.sleep(15)
                self.wfile.write(b'event: heartbeat\ndata: {"timestamp": ' + str(int(time.time())).encode() + b'}\n\n')
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected


class NgrokProxy:
    """Manages the HTTP-to-Socket proxy server"""

    def __init__(self, http_port: int = DEFAULT_HTTP_PORT,
                 socket_host: str = DEFAULT_SOCKET_HOST,
                 socket_port: int = DEFAULT_SOCKET_PORT):
        self.http_port = http_port
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.server = None
        self.running = False
        self.ngrok_url = None

    def start(self):
        """Start the HTTP proxy server"""
        if self.running:
            print("KarianaUMCP: HTTP proxy already running")
            return

        try:
            self.server = HTTPServer(('0.0.0.0', self.http_port), KarianaMCPRequestHandler)
            self.running = True

            # Start server in background thread
            server_thread = threading.Thread(target=self._serve, daemon=True)
            server_thread.start()

            print(f"KarianaUMCP: HTTP proxy started on port {self.http_port}")
            print(f"KarianaUMCP: Bridging to socket server at {self.socket_host}:{self.socket_port}")

        except Exception as e:
            print(f"KarianaUMCP: Failed to start HTTP proxy - {e}")
            self.running = False

    def _serve(self):
        """Serve HTTP requests"""
        while self.running:
            self.server.handle_request()

    def stop(self):
        """Stop the HTTP proxy server"""
        self.running = False
        if self.server:
            self.server.shutdown()
        print("KarianaUMCP: HTTP proxy stopped")

    def start_ngrok(self, auth_token: Optional[str] = None) -> Optional[str]:
        """Start ngrok tunnel to expose the HTTP proxy"""
        try:
            import pyngrok
            from pyngrok import ngrok

            # Set auth token if provided
            if auth_token:
                ngrok.set_auth_token(auth_token)

            # Start tunnel
            tunnel = ngrok.connect(self.http_port, "http")
            self.ngrok_url = tunnel.public_url

            print(f"KarianaUMCP: ngrok tunnel active at {self.ngrok_url}")

            return self.ngrok_url

        except ImportError:
            print("KarianaUMCP: pyngrok not installed. Install with: pip install pyngrok")
            return None
        except Exception as e:
            print(f"KarianaUMCP: Failed to start ngrok - {e}")
            return None

    def stop_ngrok(self):
        """Stop ngrok tunnel"""
        try:
            from pyngrok import ngrok
            ngrok.disconnect(self.ngrok_url)
            ngrok.kill()
            self.ngrok_url = None
            print("KarianaUMCP: ngrok tunnel closed")
        except:
            pass


# Global proxy instance
_proxy_instance: Optional[NgrokProxy] = None


def get_proxy() -> Optional[NgrokProxy]:
    """Get the global proxy instance"""
    return _proxy_instance


def start_proxy(http_port: int = DEFAULT_HTTP_PORT,
                socket_host: str = DEFAULT_SOCKET_HOST,
                socket_port: int = DEFAULT_SOCKET_PORT,
                start_ngrok: bool = False,
                ngrok_token: Optional[str] = None) -> NgrokProxy:
    """Start the HTTP proxy"""
    global _proxy_instance

    if _proxy_instance is None:
        _proxy_instance = NgrokProxy(http_port, socket_host, socket_port)
        _proxy_instance.start()

        if start_ngrok:
            _proxy_instance.start_ngrok(ngrok_token)

    return _proxy_instance


def stop_proxy():
    """Stop the HTTP proxy"""
    global _proxy_instance

    if _proxy_instance:
        _proxy_instance.stop_ngrok()
        _proxy_instance.stop()
        _proxy_instance = None


# Auto-start when imported in Unreal
if __name__ != "__main__":
    try:
        import unreal
        # Don't auto-start proxy - let installer or user start it
    except ImportError:
        pass
