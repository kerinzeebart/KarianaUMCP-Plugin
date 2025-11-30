"""
KarianaUMCP Instance Manager
============================
Handles automatic instance detection, authentication, and multi-instance management.

Features:
- Auto-detect existing KarianaUMCP instances
- Generate unique instance tokens
- Port allocation with fallback
- Instance registration and discovery
"""

import socket
import json
import os
import secrets
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path

from logger import get_logger

logger = get_logger("instance_manager")


class InstanceManager:
    """Manages multiple KarianaUMCP instances"""

    # Port range for KarianaUMCP instances
    BASE_PORT = 9877
    PORT_RANGE = 10  # 9877-9886

    # Instance registry file
    REGISTRY_FILE = ".kariana_instances.json"

    # Rate limiting settings
    PIN_MAX_ATTEMPTS = 5
    PIN_LOCKOUT_SECONDS = 300  # 5 minutes

    def __init__(self):
        self.instance_id: str = self._generate_instance_id()
        self.token: str = self._generate_token()
        self.pin: str = self._generate_pin()  # Simple 4-digit PIN for UI auth
        self.port: int = self.BASE_PORT
        self.project_name: str = self._get_project_name()
        self.registry_path: Path = self._get_registry_path()
        self._pin_attempts: Dict[str, List[float]] = {}  # IP -> list of attempt timestamps

    def _generate_instance_id(self) -> str:
        """Generate unique instance ID based on process and time"""
        pid = os.getpid()
        timestamp = int(time.time() * 1000)
        random_bits = secrets.token_hex(4)
        return f"kariana-{pid}-{timestamp}-{random_bits}"

    def _generate_token(self) -> str:
        """Generate secure authentication token"""
        return secrets.token_urlsafe(32)

    def _generate_pin(self) -> str:
        """Generate a simple 4-digit PIN for user-friendly authentication"""
        import random
        return str(random.randint(1000, 9999))

    def _check_rate_limit(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if client IP is rate-limited.
        Returns (allowed, remaining_seconds)
        """
        now = time.time()

        # Clean up old attempts
        if client_ip in self._pin_attempts:
            self._pin_attempts[client_ip] = [
                t for t in self._pin_attempts[client_ip]
                if now - t < self.PIN_LOCKOUT_SECONDS
            ]

        attempts = self._pin_attempts.get(client_ip, [])
        if len(attempts) >= self.PIN_MAX_ATTEMPTS:
            oldest = min(attempts)
            remaining = int(self.PIN_LOCKOUT_SECONDS - (now - oldest))
            return False, max(0, remaining)

        return True, 0

    def _record_pin_attempt(self, client_ip: str):
        """Record a PIN attempt from client IP"""
        now = time.time()
        if client_ip not in self._pin_attempts:
            self._pin_attempts[client_ip] = []
        self._pin_attempts[client_ip].append(now)

    def validate_pin(self, pin: str, client_ip: str = "unknown") -> Tuple[bool, str]:
        """
        Validate PIN for Gradio UI authentication with rate-limiting.
        Returns (success, message)
        """
        # Check rate limit
        allowed, remaining = self._check_rate_limit(client_ip)
        if not allowed:
            return False, f"Too many attempts. Try again in {remaining} seconds."

        # Record attempt before validation
        self._record_pin_attempt(client_ip)

        if not pin or len(pin) != 4:
            return False, "Invalid PIN format (must be 4 digits)"

        if secrets.compare_digest(pin, self.pin):
            # Clear attempts on success
            if client_ip in self._pin_attempts:
                del self._pin_attempts[client_ip]
            return True, "PIN validated successfully"

        attempts_left = self.PIN_MAX_ATTEMPTS - len(self._pin_attempts.get(client_ip, []))
        return False, f"Invalid PIN. {attempts_left} attempts remaining."

    def display_pin_notification(self):
        """Display PIN in Unreal Editor notification"""
        try:
            import unreal
            # Use log for now, notification API varies by UE version
            unreal.log(f"========================================")
            unreal.log(f"  KarianaUMCP Connection PIN: {self.pin}")
            unreal.log(f"  Port: {self.port}")
            unreal.log(f"========================================")
            unreal.log(f"Enter this PIN in the Kariana UI to connect")
        except ImportError:
            # Fallback for non-Unreal environment - use logger instead of print
            logger.info("=" * 40)
            logger.info(f"  KarianaUMCP Connection PIN: {self.pin}")
            logger.info(f"  Port: {self.port}")
            logger.info("=" * 40)
            logger.info("Enter this PIN in the Kariana UI to connect")

    def _get_project_name(self) -> str:
        """Get current Unreal project name"""
        try:
            import unreal
            # Try to get project name from world
            world = unreal.EditorLevelLibrary.get_editor_world()
            if world:
                return world.get_name()
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Could not get project name from Unreal: {e}")

        # Fallback: use directory name
        try:
            cwd = os.getcwd()
            return os.path.basename(cwd)
        except OSError as e:
            logger.debug(f"Could not get cwd: {e}")
            return "Unknown"

    def _get_registry_path(self) -> Path:
        """Get path to instance registry file"""
        # Use temp directory for cross-process visibility
        import tempfile
        return Path(tempfile.gettempdir()) / self.REGISTRY_FILE

    def discover_instances(self) -> List[Dict[str, Any]]:
        """Discover all running KarianaUMCP instances"""
        instances = []

        for port in range(self.BASE_PORT, self.BASE_PORT + self.PORT_RANGE):
            instance = self._probe_instance(port)
            if instance:
                instances.append(instance)

        return instances

    def _probe_instance(self, port: int, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Probe a port to check for KarianaUMCP instance"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect(('localhost', port))

            # Send discovery request
            request = {"type": "get_instance_info"}
            sock.send((json.dumps(request) + '\n').encode('utf-8'))

            # Receive response
            response = sock.recv(4096).decode('utf-8')
            sock.close()

            data = json.loads(response.strip())
            if data.get("success") and data.get("server") == "KarianaUMCP":
                return {
                    "port": port,
                    "instance_id": data.get("instance_id", "unknown"),
                    "project": data.get("project", "unknown"),
                    "version": data.get("version", "1.0.0"),
                    "token_required": data.get("token_required", False),
                    "uptime": data.get("uptime", 0)
                }
        except (socket.error, socket.timeout, json.JSONDecodeError, ConnectionRefusedError):
            # Expected errors when port is not responding or not KarianaUMCP
            pass
        except Exception as e:
            logger.debug(f"Unexpected error probing port {port}: {e}")

        return None

    def find_available_port(self) -> int:
        """Find an available port in the range"""
        for port in range(self.BASE_PORT, self.BASE_PORT + self.PORT_RANGE):
            if self._is_port_available(port):
                return port

        # All ports in range are taken - return base port and let caller handle conflict
        return self.BASE_PORT

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for binding"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result != 0  # Port available if connection failed
        except socket.error:
            return True
        except Exception as e:
            logger.debug(f"Error checking port {port}: {e}")
            return True

    def register_instance(self) -> Dict[str, Any]:
        """Register this instance in the registry"""
        registry = self._load_registry()

        instance_info = {
            "instance_id": self.instance_id,
            "port": self.port,
            "project": self.project_name,
            "token_hash": hashlib.sha256(self.token.encode()).hexdigest(),
            "pid": os.getpid(),
            "started": time.time()
        }

        registry[self.instance_id] = instance_info
        self._save_registry(registry)

        return instance_info

    def unregister_instance(self):
        """Remove this instance from the registry"""
        registry = self._load_registry()
        if self.instance_id in registry:
            del registry[self.instance_id]
            self._save_registry(registry)

    def _load_registry(self) -> Dict[str, Any]:
        """Load instance registry from file"""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.debug(f"Could not load registry: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error loading registry: {e}")
        return {}

    def _save_registry(self, registry: Dict[str, Any]):
        """Save instance registry to file"""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
        except IOError as e:
            logger.warning(f"Could not save registry: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error saving registry: {e}")

    def cleanup_stale_instances(self):
        """Remove instances that are no longer running"""
        registry = self._load_registry()
        cleaned = {}

        for instance_id, info in registry.items():
            port = info.get("port", 0)
            if self._probe_instance(port):
                cleaned[instance_id] = info

        if len(cleaned) != len(registry):
            self._save_registry(cleaned)

    def validate_token(self, token: str) -> bool:
        """Validate an authentication token"""
        return secrets.compare_digest(token, self.token)

    def get_instance_info(self) -> Dict[str, Any]:
        """Get this instance's information for discovery"""
        return {
            "success": True,
            "server": "KarianaUMCP",
            "instance_id": self.instance_id,
            "project": self.project_name,
            "version": "1.0.0",
            "port": self.port,
            "token_required": True,
            "pin_auth_available": True,
            "uptime": int(time.time() - self._start_time) if hasattr(self, '_start_time') else 0
        }

    def handle_takeover_request(self, requester_token: str) -> Tuple[bool, str]:
        """
        Handle request from another instance to take over this port.
        Returns (success, message)
        """
        # For now, allow takeover if token is valid
        # In production, you might want additional checks
        if self.validate_token(requester_token):
            return True, "Takeover authorized"
        return False, "Invalid token"


class AuthenticationMiddleware:
    """Authentication middleware for socket server"""

    def __init__(self, instance_manager: InstanceManager, require_auth: bool = False):
        self.instance_manager = instance_manager
        self.require_auth = require_auth
        self.authenticated_clients: Dict[str, float] = {}  # client_id -> auth_time
        self.auth_timeout = 3600  # 1 hour

    def authenticate(self, client_id: str, token: str) -> bool:
        """Authenticate a client with a token"""
        if self.instance_manager.validate_token(token):
            self.authenticated_clients[client_id] = time.time()
            return True
        return False

    def is_authenticated(self, client_id: str) -> bool:
        """Check if a client is authenticated"""
        if not self.require_auth:
            return True

        auth_time = self.authenticated_clients.get(client_id)
        if auth_time and (time.time() - auth_time) < self.auth_timeout:
            return True

        # Remove expired authentication
        if client_id in self.authenticated_clients:
            del self.authenticated_clients[client_id]

        return False

    def requires_auth(self, command_type: str) -> bool:
        """Check if a command requires authentication"""
        # These commands are always allowed without auth (for discovery)
        public_commands = {
            "ping",
            "get_instance_info",
            "get_server_info",
            "authenticate"
        }
        return command_type not in public_commands and self.require_auth


# Global instance manager
_instance_manager: Optional[InstanceManager] = None


def get_instance_manager() -> InstanceManager:
    """Get or create the global instance manager"""
    global _instance_manager
    if _instance_manager is None:
        _instance_manager = InstanceManager()
    return _instance_manager


def auto_configure() -> Dict[str, Any]:
    """
    Auto-configure the server based on existing instances.
    Returns configuration dict with port and instance info.
    """
    manager = get_instance_manager()

    # Clean up stale instances first
    manager.cleanup_stale_instances()

    # Discover existing instances
    existing = manager.discover_instances()

    # Find available port
    manager.port = manager.find_available_port()

    # Mark start time
    manager._start_time = time.time()

    # Register this instance
    manager.register_instance()

    # Display PIN notification for easy UI connection
    manager.display_pin_notification()

    return {
        "instance_id": manager.instance_id,
        "port": manager.port,
        "token": manager.token,
        "pin": manager.pin,
        "project": manager.project_name,
        "existing_instances": existing
    }


# Export
__all__ = [
    'InstanceManager',
    'AuthenticationMiddleware',
    'get_instance_manager',
    'auto_configure'
]
