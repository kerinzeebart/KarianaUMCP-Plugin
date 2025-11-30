"""
KarianaUMCP Socket Server
=========================
Central orchestrator for all MCP tool requests.
Listens on port 9877 for JSON commands.

Features:
- Automatic instance detection and port allocation
- Token-based authentication
- Multi-instance support with discovery
- Based on battle-tested UMCPitv20 implementation
- Compatible with FastMCP 2.13+
"""

import socket
import threading
import json
import traceback
import time
import secrets
from typing import Dict, Any, Callable, Optional
import sys
import os

# Add plugin directory to path
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

# Import logger early
from logger import get_logger
logger = get_logger("socket_server")

# Import instance manager
try:
    from instance_manager import (
        InstanceManager,
        AuthenticationMiddleware,
        get_instance_manager,
        auto_configure
    )
    INSTANCE_MANAGER_AVAILABLE = True
except ImportError:
    INSTANCE_MANAGER_AVAILABLE = False

# Import skills loader (progressive disclosure architecture)
try:
    from skills_loader import (
        get_skills_loader,
        discover_skills as discover_skills_func,
        load_skill as load_skill_func,
        find_skills as find_skills_func
    )
    SKILLS_LOADER_AVAILABLE = True
except ImportError:
    SKILLS_LOADER_AVAILABLE = False


class KarianaSocketServer:
    """Main socket server for MCP tool requests with instance management"""

    def __init__(self, host: str = "localhost", port: int = 9877, require_auth: bool = False):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.handlers: Dict[str, Callable] = {}
        self.skills: Dict[str, Any] = {}
        self.start_time = time.time()

        # Instance management
        self.instance_manager: Optional[InstanceManager] = None
        self.auth_middleware: Optional[AuthenticationMiddleware] = None
        self.require_auth = require_auth

        # Initialize instance management if available
        if INSTANCE_MANAGER_AVAILABLE:
            self._init_instance_management()

        # Load handlers and skills
        self._load_handlers()
        self._load_skills()

    def _init_instance_management(self):
        """Initialize instance management and auto-configure"""
        config = auto_configure()

        self.instance_manager = get_instance_manager()
        self.port = config["port"]  # Use auto-allocated port

        # Set up authentication middleware
        self.auth_middleware = AuthenticationMiddleware(
            self.instance_manager,
            require_auth=self.require_auth
        )

        # Log discovered instances
        existing = config.get("existing_instances", [])
        if existing:
            logger.info(f"Found {len(existing)} existing instance(s)")
            for inst in existing:
                logger.info(f"  - Port {inst['port']}: {inst['project']} ({inst['instance_id'][:20]}...)")

        logger.info(f"Instance ID: {config['instance_id'][:20]}...")
        logger.debug(f"Auth token: {config['token'][:8]}... (save for authentication)")

    def _load_handlers(self):
        """Load all command handlers from handlers/ directory"""
        handlers_dir = os.path.join(PLUGIN_DIR, "handlers")

        # Core handlers with their commands
        self.handlers = {
            # System commands
            "list_functions": self._handle_list_functions,
            "ping": self._handle_ping,
            "get_server_info": self._handle_server_info,

            # Instance management (public - no auth required)
            "get_instance_info": self._handle_instance_info,
            "discover_instances": self._handle_discover_instances,
            "authenticate": self._handle_authenticate,
            "validate_pin": self._handle_validate_pin,
            "get_pin": self._handle_get_pin,

            # Python execution - supports both 'code' and 'script' params
            "execute_python": self._handle_execute_python,
            "run_python": self._handle_execute_python,

            # Actor operations (from ops/actor.py)
            "spawn_actor": self._handle_actor_command,
            "delete_actor": self._handle_actor_command,
            "get_actor_location": self._handle_actor_command,
            "set_actor_location": self._handle_actor_command,
            "set_actor_rotation": self._handle_actor_command,
            "set_actor_scale": self._handle_actor_command,
            "modify_actor_property": self._handle_actor_command,
            "list_actors": self._handle_actor_command,

            # Blueprint operations (from ops/blueprint.py)
            "create_blueprint": self._handle_blueprint_command,
            "add_blueprint_component": self._handle_blueprint_command,
            "get_blueprint_info": self._handle_blueprint_command,
            "compile_blueprint": self._handle_blueprint_command,
            "open_blueprint_editor": self._handle_blueprint_command,
            "set_component_property": self._handle_blueprint_command,
            "set_component_transform": self._handle_blueprint_command,
            "get_blueprint_components": self._handle_blueprint_command,

            # Asset operations (from ops/asset.py)
            "import_asset": self._handle_asset_command,
            "list_assets": self._handle_asset_command,
            "create_material": self._handle_asset_command,
            "get_asset_info": self._handle_asset_command,
            "save_asset": self._handle_asset_command,

            # Level operations (from ops/level.py)
            "load_level": self._handle_level_command,
            "save_level": self._handle_level_command,
            "get_current_level": self._handle_level_command,
            "list_levels": self._handle_level_command,

            # System operations (from ops/system.py)
            "console_command": self._handle_system_command,
            "get_ue_logs": self._handle_system_command,
            "get_engine_info": self._handle_system_command,
            "capture_screenshot": self._handle_screenshot,

            # Editor control
            "play_in_editor": self._handle_editor_command,
            "stop_play_in_editor": self._handle_editor_command,
            "set_camera_location": self._handle_editor_command,

            # Skills execution (progressive disclosure)
            "execute_skill": self._handle_skill_execution,
            "list_skills": self._handle_list_skills,
            "discover_skills": self._handle_discover_skills,
            "load_skill": self._handle_load_skill,
            "find_skills": self._handle_find_skills,

            # Blueprint Intelligence
            "auto_wire_blueprint": self._handle_blueprint_intelligence,
            "find_compatible_pins": self._handle_blueprint_intelligence,

            # Selection handlers (Content Browser & Viewport)
            "get_selected_assets": self._handle_get_selected_assets,
            "get_selected_actors": self._handle_get_selected_actors,

            # Function router (for execute_function calls)
            "execute_function": self._handle_execute_function,

            # Viewport operations (from ops/viewport.py)
            "focus_on_actor": self._handle_viewport_command,
            "set_render_mode": self._handle_viewport_command,
            "look_at_target": self._handle_viewport_command,
            "set_view_mode": self._handle_viewport_command,
            "fit_actors": self._handle_viewport_command,
            "get_viewport_bounds": self._handle_viewport_command,
            "set_camera": self._handle_viewport_command,

            # Organization operations (from ops/organization.py)
            "create_folder_structure": self._handle_organization_command,
            "organize_assets_by_type": self._handle_organization_command,
            "organize_world_outliner": self._handle_organization_command,
            "tag_assets": self._handle_organization_command,
            "search_assets_by_tag": self._handle_organization_command,
            "generate_organization_report": self._handle_organization_command,

            # Blueprint connection operations (from ops/blueprint_connections.py)
            "get_blueprint_node_pins": self._handle_blueprint_connection_command,
            "validate_blueprint_connection": self._handle_blueprint_connection_command,
            "auto_connect_blueprint_chain": self._handle_blueprint_connection_command,
            "suggest_blueprint_connections": self._handle_blueprint_connection_command,
            "get_blueprint_graph_connections": self._handle_blueprint_connection_command,

            # Material operations (from ops/material.py)
            "list_materials": self._handle_material_command,
            "get_material_info": self._handle_material_command,
            "create_material_instance": self._handle_material_command,
            "apply_material_to_actor": self._handle_material_command,
            "create_simple_material": self._handle_material_command,

            # Validation operations (from ops/validation.py)
            "validate_actor_spawn": self._handle_validation_command,
            "validate_actor_location": self._handle_validation_command,
            "validate_actor_rotation": self._handle_validation_command,
            "validate_actor_scale": self._handle_validation_command,
            "validate_actor_exists": self._handle_validation_command,
            "validate_actor_deleted": self._handle_validation_command,
            "validate_placement": self._handle_validation_command,

            # Physics operations (from ops/physics.py)
            "enable_physics_on_actor": self._handle_physics_command,
            "disable_physics_on_actor": self._handle_physics_command,
            "get_actor_physics_status": self._handle_physics_command,
        }

        logger.info(f"Loaded {len(self.handlers)} command handlers")

    def _load_skills(self):
        """Load skills using progressive disclosure architecture"""
        # First try new skills_loader (SKILL.md format)
        if SKILLS_LOADER_AVAILABLE:
            try:
                loader = get_skills_loader()
                skill_metadata = loader.discover_skills()
                for metadata in skill_metadata:
                    self.skills[metadata.name] = {
                        "name": metadata.name,
                        "description": metadata.description,
                        "version": metadata.version,
                        "author": metadata.author,
                        "dependencies": metadata.dependencies,
                        "path": metadata.path,
                        "_loader": "skills_loader"  # Mark source
                    }
                logger.info(f"Discovered {len(skill_metadata)} skills (SKILL.md format)")
            except Exception as e:
                logger.warning(f"Skills loader error: {e}")

        # Also load legacy JSON manifests for backwards compatibility
        skills_dir = os.path.join(PLUGIN_DIR, "skills", "manifests")
        if os.path.exists(skills_dir):
            for filename in os.listdir(skills_dir):
                if filename.endswith(".skill.json"):
                    try:
                        with open(os.path.join(skills_dir, filename), 'r') as f:
                            skill = json.load(f)
                            skill_name = skill.get("name", filename)
                            if skill_name not in self.skills:  # Don't override new format
                                skill["_loader"] = "legacy_json"
                                self.skills[skill_name] = skill
                    except (IOError, json.JSONDecodeError) as e:
                        logger.warning(f"Failed to load skill {filename}: {e}")

        logger.info(f"Total skills loaded: {len(self.skills)}")

    def start(self):
        """Start the socket server"""
        if self.running:
            logger.warning("Server already running")
            return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            logger.info(f"Socket server started on {self.host}:{self.port}")

            # Accept connections in a loop
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()

        except OSError as e:
            logger.error(f"Failed to start server - {e}")
            self.running = False

    def stop(self):
        """Stop the socket server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("Socket server stopped")

    def _accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
            except OSError as e:
                if self.running:
                    logger.error(f"Connection error - {e}")

    def _handle_client(self, client_socket: socket.socket, address):
        """Handle a single client connection"""
        buffer = ""
        client_ip = address[0] if address else "unknown"
        try:
            while self.running:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break

                buffer += data

                # Process complete JSON messages (newline-delimited)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        response = self._process_message(line.strip(), client_ip=client_ip)
                        client_socket.send((json.dumps(response) + '\n').encode('utf-8'))

        except (socket.error, UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.debug(f"Client error - {e}")
        finally:
            client_socket.close()

    # Commands that DON'T need main thread (can run on any thread)
    THREAD_SAFE_COMMANDS = {
        "ping", "get_server_info", "get_instance_info", "list_functions",
        "list_skills", "validate_pin", "authenticate", "discover_instances"
    }

    def _process_message(self, message: str, client_ip: str = "unknown") -> Dict[str, Any]:
        """Process a JSON message and return response"""
        try:
            data = json.loads(message)
            data["_client_ip"] = client_ip  # Inject client IP for rate-limiting
            command_type = data.get("type", "")

            # Find handler for command
            handler = self.handlers.get(command_type)
            if handler:
                # Check if command needs main thread
                if command_type in self.THREAD_SAFE_COMMANDS:
                    # Safe to run directly
                    return handler(data)
                else:
                    # Need main thread for Unreal API calls
                    return self._execute_on_main_thread(handler, data, command_type)
            else:
                return {
                    "success": False,
                    "error": f"Unknown command: {command_type}",
                    "available_commands": list(self.handlers.keys())
                }

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    # Commands that need longer timeouts (heavy operations)
    HEAVY_COMMANDS = {
        "capture_screenshot": 60.0,
        "execute_python": 30.0,
        "compile_blueprint": 30.0,
        "execute_skill": 60.0,
        "import_asset": 60.0,
        "build_lighting": 120.0,
    }

    def _execute_on_main_thread(self, handler, data: Dict, command_type: str) -> Dict:
        """Execute handler on main thread using the tick callback queue.

        The main_thread_executor registers a slate tick callback during init
        (on the main thread). Commands are queued and processed each tick.
        """
        # Get appropriate timeout for this command
        timeout = self.HEAVY_COMMANDS.get(command_type, 15.0)

        try:
            # Import the module to check current state (not a cached import)
            import main_thread_executor

            if main_thread_executor._callback_registered:
                # Use the queue mechanism
                return main_thread_executor.execute_on_main_thread(
                    lambda: handler(data), timeout=timeout
                )
            else:
                # Fallback: try direct execution (will fail for most Unreal APIs)
                return handler(data)

        except ImportError:
            # No main_thread_executor available
            return handler(data)
        except TimeoutError:
            return {"success": False, "error": f"Command '{command_type}' timed out ({timeout}s)"}
        except Exception as e:
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

    # ========== Handler Methods ==========

    def _handle_ping(self, data: Dict) -> Dict:
        """Handle ping request"""
        return {"success": True, "message": "pong", "server": "KarianaUMCP"}

    def _handle_server_info(self, data: Dict) -> Dict:
        """Return server information"""
        info = {
            "success": True,
            "server": "KarianaUMCP",
            "version": "1.0.0",
            "port": self.port,
            "handlers": len(self.handlers),
            "skills": len(self.skills),
            "uptime": int(time.time() - self.start_time)
        }

        # Add instance info if available
        if self.instance_manager:
            info["instance_id"] = self.instance_manager.instance_id
            info["project"] = self.instance_manager.project_name
            info["auth_required"] = self.require_auth

        return info

    def _handle_instance_info(self, data: Dict) -> Dict:
        """Return instance information for discovery"""
        if self.instance_manager:
            return self.instance_manager.get_instance_info()

        return {
            "success": True,
            "server": "KarianaUMCP",
            "instance_id": "legacy",
            "project": "Unknown",
            "version": "1.0.0",
            "port": self.port,
            "token_required": False,
            "uptime": int(time.time() - self.start_time)
        }

    def _handle_discover_instances(self, data: Dict) -> Dict:
        """Discover all running KarianaUMCP instances"""
        if self.instance_manager:
            instances = self.instance_manager.discover_instances()
            return {
                "success": True,
                "instances": instances,
                "count": len(instances),
                "current_instance": self.instance_manager.instance_id
            }

        return {
            "success": False,
            "error": "Instance manager not available",
            "instances": []
        }

    def _handle_authenticate(self, data: Dict) -> Dict:
        """Authenticate a client with a token"""
        token = data.get("token", "")
        client_id = data.get("client_id", "default")

        if not self.instance_manager:
            return {
                "success": True,
                "message": "Authentication not required (legacy mode)"
            }

        if self.auth_middleware and self.auth_middleware.authenticate(client_id, token):
            return {
                "success": True,
                "message": "Authentication successful",
                "client_id": client_id,
                "expires_in": self.auth_middleware.auth_timeout
            }

        return {
            "success": False,
            "error": "Invalid token"
        }

    def _handle_validate_pin(self, data: Dict) -> Dict:
        """Validate PIN for Gradio UI authentication with rate-limiting"""
        pin = data.get("pin", "")
        client_ip = data.get("_client_ip", "unknown")  # Injected by socket handler

        if not self.instance_manager:
            return {
                "success": True,
                "message": "PIN authentication not available (legacy mode)",
                "session_token": "legacy"
            }

        # Use rate-limited validation
        success, message = self.instance_manager.validate_pin(pin, client_ip)

        if success:
            # Generate session token for authenticated client
            session_token = secrets.token_urlsafe(16) if 'secrets' in dir() else self.instance_manager.token[:16]
            return {
                "success": True,
                "message": message,
                "session_token": session_token,
                "instance_id": self.instance_manager.instance_id,
                "project": self.instance_manager.project_name,
                "port": self.port
            }

        return {
            "success": False,
            "error": message
        }

    def _handle_get_pin(self, data: Dict) -> Dict:
        """Get current PIN (for debugging/display - normally shown in UE log)"""
        # Only allow in debug mode or for authenticated clients
        if not self.instance_manager:
            return {
                "success": False,
                "error": "Instance manager not available"
            }

        # Security: Don't expose PIN over network by default
        # PIN should be viewed in Unreal Editor log
        return {
            "success": True,
            "message": "PIN is displayed in Unreal Editor output log",
            "hint": "Look for 'KarianaUMCP Connection PIN' in the UE log"
        }

    def _handle_list_functions(self, data: Dict) -> Dict:
        """List all available functions with metadata"""
        functions = []

        # Core functions
        functions.extend([
            {
                "name": "ping",
                "description": "Test server connectivity",
                "parameters": {}
            },
            {
                "name": "list_functions",
                "description": "List all available MCP tools",
                "parameters": {}
            },
            {
                "name": "execute_python",
                "description": "Execute Python code in Unreal Engine",
                "parameters": {
                    "code": {"type": "string", "description": "Python code to execute", "required": True}
                }
            },
            {
                "name": "capture_screenshot",
                "description": "Capture low-resolution screenshot from viewport",
                "parameters": {
                    "width": {"type": "integer", "description": "Image width", "default": 800},
                    "height": {"type": "integer", "description": "Image height", "default": 600},
                    "quality": {"type": "integer", "description": "JPEG quality 1-100", "default": 85}
                }
            }
        ])

        # Actor functions
        for cmd in ["spawn_actor", "delete_actor", "list_actors", "get_actor_location",
                    "set_actor_location", "set_actor_rotation", "set_actor_scale", "modify_actor_property"]:
            functions.append({
                "name": cmd,
                "description": f"Actor operation: {cmd.replace('_', ' ')}",
                "parameters": self._get_actor_params(cmd)
            })

        # Blueprint functions with proper parameter schemas
        functions.append({
            "name": "create_blueprint",
            "description": "Create a new Blueprint asset",
            "parameters": {
                "name": {"type": "string", "description": "Name of the Blueprint", "required": True},
                "path": {"type": "string", "description": "Content path (e.g., /Game/Blueprints)", "default": "/Game/Blueprints"},
                "parent_class": {"type": "string", "description": "Parent class (Actor, Pawn, Character)", "default": "Actor"}
            }
        })
        functions.append({
            "name": "add_blueprint_component",
            "description": "Add a component to a Blueprint",
            "parameters": {
                "blueprint_path": {"type": "string", "description": "Path to Blueprint (e.g., /Game/Blueprints/MyBP)", "required": True},
                "component_type": {"type": "string", "description": "Component type (StaticMeshComponent, PointLightComponent, etc.)", "required": True},
                "name": {"type": "string", "description": "Name for the new component", "default": "NewComponent"},
                "parent": {"type": "string", "description": "Parent component name to attach to"}
            }
        })
        functions.append({
            "name": "get_blueprint_info",
            "description": "Get information about a Blueprint",
            "parameters": {
                "blueprint_path": {"type": "string", "description": "Path to Blueprint (e.g., /Game/Blueprints/MyBP)", "required": True}
            }
        })
        functions.append({
            "name": "compile_blueprint",
            "description": "Compile a Blueprint",
            "parameters": {
                "blueprint_path": {"type": "string", "description": "Path to Blueprint (e.g., /Game/Blueprints/MyBP)", "required": True}
            }
        })
        functions.append({
            "name": "open_blueprint_editor",
            "description": "Open a Blueprint in the editor",
            "parameters": {
                "blueprint_path": {"type": "string", "description": "Path to Blueprint (e.g., /Game/Blueprints/MyBP)", "required": True}
            }
        })

        # Asset functions with proper parameter schemas
        functions.append({
            "name": "import_asset",
            "description": "Import an external file as an asset",
            "parameters": {
                "source_path": {"type": "string", "description": "Path to source file on disk", "required": True},
                "destination_path": {"type": "string", "description": "Content path to import to (e.g., /Game/Textures)", "required": True},
                "asset_name": {"type": "string", "description": "Name for the imported asset"}
            }
        })
        functions.append({
            "name": "list_assets",
            "description": "List assets in a content folder",
            "parameters": {
                "path": {"type": "string", "description": "Content path to list (e.g., /Game/Blueprints)", "default": "/Game"},
                "asset_type": {"type": "string", "description": "Filter by asset type (Blueprint, Material, Texture, etc.)"},
                "recursive": {"type": "boolean", "description": "Search recursively", "default": False}
            }
        })
        functions.append({
            "name": "create_material",
            "description": "Create a new material asset",
            "parameters": {
                "name": {"type": "string", "description": "Name of the material", "required": True},
                "path": {"type": "string", "description": "Content path (e.g., /Game/Materials)", "default": "/Game/Materials"},
                "base_color": {"type": "array", "description": "[R, G, B, A] values 0-1"},
                "metallic": {"type": "number", "description": "Metallic value 0-1"},
                "roughness": {"type": "number", "description": "Roughness value 0-1"}
            }
        })
        functions.append({
            "name": "get_asset_info",
            "description": "Get information about an asset",
            "parameters": {
                "asset_path": {"type": "string", "description": "Path to asset (e.g., /Game/Blueprints/MyBP)", "required": True}
            }
        })
        functions.append({
            "name": "save_asset",
            "description": "Save an asset to disk",
            "parameters": {
                "asset_path": {"type": "string", "description": "Path to asset (e.g., /Game/Blueprints/MyBP)", "required": True}
            }
        })

        # Editor functions
        for cmd in ["play_in_editor", "stop_play_in_editor", "set_camera_location"]:
            functions.append({
                "name": cmd,
                "description": f"Editor control: {cmd.replace('_', ' ')}",
                "parameters": {}
            })

        # Skills
        functions.append({
            "name": "list_skills",
            "description": "List all available skills",
            "parameters": {}
        })
        functions.append({
            "name": "execute_skill",
            "description": "Execute a skill by name",
            "parameters": {
                "skill_name": {"type": "string", "description": "Name of skill to execute", "required": True}
            }
        })

        # Blueprint Intelligence
        functions.append({
            "name": "auto_wire_blueprint",
            "description": "Automatically wire Blueprint nodes",
            "parameters": {
                "blueprint_path": {"type": "string", "description": "Path to Blueprint", "required": True}
            }
        })
        functions.append({
            "name": "find_compatible_pins",
            "description": "Find compatible pins for a node in a Blueprint",
            "parameters": {
                "blueprint_path": {"type": "string", "description": "Path to Blueprint", "required": True},
                "node_name": {"type": "string", "description": "Name of the node", "required": True}
            }
        })

        # Selection functions
        functions.append({
            "name": "get_selected_assets",
            "description": "Get currently selected assets in Content Browser",
            "parameters": {}
        })
        functions.append({
            "name": "get_selected_actors",
            "description": "Get currently selected actors in viewport/outliner",
            "parameters": {
                "include_details": {"type": "boolean", "description": "Include transform details", "default": True}
            }
        })

        # Viewport functions
        functions.extend([
            {
                "name": "focus_on_actor",
                "description": "Focus viewport camera on a specific actor",
                "parameters": {
                    "actor_name": {"type": "string", "description": "Name of actor to focus on", "required": True},
                    "preserve_rotation": {"type": "boolean", "description": "Keep current camera angles", "default": False}
                }
            },
            {
                "name": "set_render_mode",
                "description": "Change viewport rendering mode (lit, unlit, wireframe, etc.)",
                "parameters": {
                    "mode": {"type": "string", "description": "Render mode: lit, unlit, wireframe, detail_lighting, lighting_only, light_complexity, shader_complexity", "required": True}
                }
            },
            {
                "name": "look_at_target",
                "description": "Point viewport camera to look at specific coordinates or actor",
                "parameters": {
                    "target": {"type": "array", "description": "[X, Y, Z] target location"},
                    "actor_name": {"type": "string", "description": "Name of actor to look at"},
                    "distance": {"type": "number", "description": "Distance from target", "default": 1000},
                    "pitch": {"type": "number", "description": "Camera pitch angle", "default": -30},
                    "height": {"type": "number", "description": "Camera height offset", "default": 500}
                }
            },
            {
                "name": "set_view_mode",
                "description": "Position camera for standard views (top, front, side, etc.)",
                "parameters": {
                    "mode": {"type": "string", "description": "View mode: perspective, top, bottom, left, right, front, back", "required": True}
                }
            },
            {
                "name": "fit_actors",
                "description": "Fit actors in viewport by adjusting camera position",
                "parameters": {
                    "actors": {"type": "array", "description": "List of actor names to fit"},
                    "filter": {"type": "string", "description": "Pattern to filter actor names"},
                    "padding": {"type": "number", "description": "Padding percentage", "default": 20}
                }
            },
            {
                "name": "get_viewport_bounds",
                "description": "Get current viewport boundaries and camera info",
                "parameters": {}
            },
            {
                "name": "set_camera",
                "description": "Set viewport camera position and rotation",
                "parameters": {
                    "location": {"type": "array", "description": "[X, Y, Z] camera location"},
                    "rotation": {"type": "array", "description": "[Roll, Pitch, Yaw] camera rotation"},
                    "focus_actor": {"type": "string", "description": "Name of actor to focus on"},
                    "distance": {"type": "number", "description": "Distance from focus actor", "default": 500}
                }
            }
        ])

        return {
            "success": True,
            "functions": functions,
            "count": len(functions)
        }

    def _get_actor_params(self, cmd: str) -> Dict:
        """Get parameters for actor commands"""
        params = {
            "spawn_actor": {
                "actor_class": {"type": "string", "description": "Actor class to spawn", "required": True},
                "location": {"type": "array", "description": "[x, y, z] location"},
                "rotation": {"type": "array", "description": "[pitch, yaw, roll] rotation"},
                "name": {"type": "string", "description": "Actor label"}
            },
            "delete_actor": {
                "actor_name": {"type": "string", "description": "Name of actor to delete", "required": True}
            },
            "list_actors": {
                "class_filter": {"type": "string", "description": "Filter by class name"}
            },
            "get_actor_location": {
                "actor_name": {"type": "string", "description": "Name of actor", "required": True}
            },
            "set_actor_location": {
                "actor_name": {"type": "string", "description": "Name of actor", "required": True},
                "location": {"type": "array", "description": "[x, y, z] location", "required": True}
            },
            "set_actor_rotation": {
                "actor_name": {"type": "string", "description": "Name of actor", "required": True},
                "rotation": {"type": "array", "description": "[pitch, yaw, roll] rotation", "required": True}
            },
            "set_actor_scale": {
                "actor_name": {"type": "string", "description": "Name of actor", "required": True},
                "scale": {"type": "array", "description": "[x, y, z] scale", "required": True}
            },
            "modify_actor_property": {
                "actor_name": {"type": "string", "description": "Name of actor", "required": True},
                "property_name": {"type": "string", "description": "Property to modify", "required": True},
                "value": {"type": "any", "description": "New value", "required": True}
            }
        }
        return params.get(cmd, {})

    def _handle_execute_python(self, data: Dict) -> Dict:
        """Execute Python code in Unreal Engine"""
        # Support both 'code' and 'script' parameter names
        code = data.get("code") or data.get("script", "")

        if not code:
            return {
                "success": False,
                "error": "No code provided. Include 'code' or 'script' parameter."
            }

        try:
            import unreal

            # Capture output
            import io
            import sys

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()

            result = None
            try:
                # Execute the code
                exec_globals = {"unreal": unreal, "result": None}
                exec(code, exec_globals)
                result = exec_globals.get("result")

                stdout_output = sys.stdout.getvalue()
                stderr_output = sys.stderr.getvalue()

            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            response = {"success": True}
            if result is not None:
                response["result"] = str(result)
            if stdout_output:
                response["output"] = stdout_output
            if stderr_output:
                response["stderr"] = stderr_output

            return response

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    def _handle_screenshot(self, data: Dict) -> Dict:
        """Capture screenshot using PIL"""
        width = data.get("width", 800)
        height = data.get("height", 600)
        quality = data.get("quality", 85)

        try:
            from ops.screenshot import capture_screenshot_mcp
            return capture_screenshot_mcp(width, height, quality)
        except ImportError:
            # Fallback implementation
            return self._capture_screenshot_fallback(width, height, quality)

    def _capture_screenshot_fallback(self, width: int, height: int, quality: int) -> Dict:
        """Fallback screenshot capture"""
        try:
            import unreal
            import tempfile
            import os
            import base64

            # Take screenshot
            temp_path = os.path.join(tempfile.gettempdir(), "kariana_screenshot.png")
            unreal.AutomationLibrary.take_high_res_screenshot(
                width, height, temp_path
            )

            # Try PIL compression if available
            try:
                from PIL import Image
                import io

                img = Image.open(temp_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                img_bytes = buffer.getvalue()
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                return {
                    "success": True,
                    "image": img_base64,
                    "size": len(img_bytes),
                    "format": "jpeg",
                    "dimensions": {"width": width, "height": height}
                }

            except ImportError:
                # Return raw PNG if PIL not available
                with open(temp_path, 'rb') as f:
                    img_bytes = f.read()

                return {
                    "success": True,
                    "image": base64.b64encode(img_bytes).decode('utf-8'),
                    "size": len(img_bytes),
                    "format": "png",
                    "dimensions": {"width": width, "height": height},
                    "warning": "PIL not installed - returning uncompressed PNG"
                }

        except Exception as e:
            return {"success": False, "error": f"Screenshot failed: {e}"}

    def _handle_actor_command(self, data: Dict) -> Dict:
        """Route actor commands to ops/actor.py"""
        try:
            from ops.actor import handle_actor_command
            return handle_actor_command(data)
        except ImportError:
            return self._actor_command_fallback(data)

    def _actor_command_fallback(self, data: Dict) -> Dict:
        """Fallback actor command handler"""
        cmd = data.get("type", "")

        try:
            import unreal

            if cmd == "list_actors":
                actors = unreal.EditorLevelLibrary.get_all_level_actors()
                return {
                    "success": True,
                    "actors": [a.get_actor_label() for a in actors],
                    "count": len(actors)
                }

            elif cmd == "spawn_actor":
                actor_class = data.get("actor_class", "StaticMeshActor")
                location = data.get("location", [0, 0, 0])
                name = data.get("name", "")

                loc = unreal.Vector(location[0], location[1], location[2])
                rot = unreal.Rotator(0, 0, 0)

                actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                    unreal.load_class(None, f"/Script/Engine.{actor_class}"),
                    loc, rot
                )

                if actor and name:
                    actor.set_actor_label(name)

                return {
                    "success": True,
                    "actor": actor.get_actor_label() if actor else None
                }

            elif cmd == "delete_actor":
                actor_name = data.get("actor_name", "")
                actors = unreal.EditorLevelLibrary.get_all_level_actors()

                for actor in actors:
                    if actor.get_actor_label() == actor_name:
                        actor.destroy_actor()
                        return {"success": True, "deleted": actor_name}

                return {"success": False, "error": f"Actor not found: {actor_name}"}

            elif cmd == "get_actor_location":
                actor_name = data.get("actor_name", "")
                actors = unreal.EditorLevelLibrary.get_all_level_actors()

                for actor in actors:
                    if actor.get_actor_label() == actor_name:
                        loc = actor.get_actor_location()
                        return {
                            "success": True,
                            "location": [loc.x, loc.y, loc.z]
                        }

                return {"success": False, "error": f"Actor not found: {actor_name}"}

            elif cmd == "set_actor_location":
                actor_name = data.get("actor_name", "")
                location = data.get("location", [0, 0, 0])
                actors = unreal.EditorLevelLibrary.get_all_level_actors()

                for actor in actors:
                    if actor.get_actor_label() == actor_name:
                        loc = unreal.Vector(location[0], location[1], location[2])
                        actor.set_actor_location(loc, False, False)
                        return {"success": True}

                return {"success": False, "error": f"Actor not found: {actor_name}"}

            else:
                return {"success": False, "error": f"Unknown actor command: {cmd}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_blueprint_command(self, data: Dict) -> Dict:
        """Route blueprint commands"""
        try:
            from ops.blueprint import handle_blueprint_command
            return handle_blueprint_command(data)
        except ImportError:
            return {"success": False, "error": "Blueprint ops module not loaded"}

    def _handle_asset_command(self, data: Dict) -> Dict:
        """Route asset commands"""
        try:
            from ops.asset import handle_asset_command
            return handle_asset_command(data)
        except ImportError:
            cmd = data.get("type", "")
            if cmd == "list_assets":
                return self._list_assets_fallback(data)
            return {"success": False, "error": "Asset ops module not loaded"}

    def _list_assets_fallback(self, data: Dict) -> Dict:
        """Fallback asset listing"""
        try:
            import unreal
            path = data.get("path", "/Game")

            asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
            assets = asset_registry.get_assets_by_path(path, recursive=True)

            return {
                "success": True,
                "assets": [str(a.asset_name) for a in assets[:100]],
                "count": len(assets)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_level_command(self, data: Dict) -> Dict:
        """Route level commands"""
        try:
            from ops.level import handle_level_command
            return handle_level_command(data)
        except ImportError:
            return {"success": False, "error": "Level ops module not loaded"}

    def _handle_system_command(self, data: Dict) -> Dict:
        """Route system commands"""
        try:
            from ops.system import handle_system_command
            return handle_system_command(data)
        except ImportError:
            cmd = data.get("type", "")
            if cmd == "console_command":
                return self._console_command_fallback(data)
            return {"success": False, "error": "System ops module not loaded"}

    def _console_command_fallback(self, data: Dict) -> Dict:
        """Execute console command"""
        try:
            import unreal
            command = data.get("command", "")
            unreal.SystemLibrary.execute_console_command(None, command)
            return {"success": True, "command": command}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_editor_command(self, data: Dict) -> Dict:
        """Handle editor control commands"""
        cmd = data.get("type", "")

        try:
            import unreal

            if cmd == "play_in_editor":
                unreal.EditorLevelLibrary.editor_play_simulate()
                return {"success": True, "action": "play"}

            elif cmd == "stop_play_in_editor":
                unreal.EditorLevelLibrary.editor_end_play()
                return {"success": True, "action": "stop"}

            elif cmd == "set_camera_location":
                location = data.get("location", [0, 0, 0])
                rotation = data.get("rotation", [0, 0, 0])

                # Use viewport commands
                loc = unreal.Vector(location[0], location[1], location[2])
                rot = unreal.Rotator(rotation[0], rotation[1], rotation[2])

                unreal.EditorLevelLibrary.set_level_viewport_camera_info(loc, rot)
                return {"success": True}

            return {"success": False, "error": f"Unknown editor command: {cmd}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_skill_execution(self, data: Dict) -> Dict:
        """Execute a skill by name"""
        skill_name = data.get("skill_name", "")

        if skill_name not in self.skills:
            return {
                "success": False,
                "error": f"Skill not found: {skill_name}",
                "available_skills": list(self.skills.keys())
            }

        try:
            from skills.executor import execute_skill
            return execute_skill(self.skills[skill_name], data.get("parameters", {}))
        except ImportError:
            return {"success": False, "error": "Skills executor not loaded"}

    def _handle_list_skills(self, data: Dict) -> Dict:
        """List all available skills (backwards compatible)"""
        return {
            "success": True,
            "skills": [
                {
                    "name": name,
                    "description": skill.get("description", ""),
                    "version": skill.get("version", "1.0.0"),
                    "loader": skill.get("_loader", "unknown")
                }
                for name, skill in self.skills.items()
            ],
            "count": len(self.skills)
        }

    def _handle_discover_skills(self, data: Dict) -> Dict:
        """Discover available skills (Phase 1: metadata only, ~100 tokens each)"""
        if SKILLS_LOADER_AVAILABLE:
            try:
                skills = discover_skills_func()
                return {
                    "success": True,
                    "skills": skills,
                    "count": len(skills)
                }
            except Exception as e:
                return {"success": False, "error": f"Skills discovery error: {e}"}

        # Fallback to cached skills
        return self._handle_list_skills(data)

    def _handle_load_skill(self, data: Dict) -> Dict:
        """Load full skill instructions (Phase 2: <5k tokens)"""
        skill_name = data.get("skill_name", "")

        if not skill_name:
            return {"success": False, "error": "skill_name is required"}

        if SKILLS_LOADER_AVAILABLE:
            try:
                skill = load_skill_func(skill_name)
                if skill:
                    return {
                        "success": True,
                        **skill
                    }
                return {"success": False, "error": f"Skill not found: {skill_name}"}
            except Exception as e:
                return {"success": False, "error": f"Skill load error: {e}"}

        # Fallback to cached skills
        if skill_name in self.skills:
            return {
                "success": True,
                "name": skill_name,
                "description": self.skills[skill_name].get("description", ""),
                "instructions": self.skills[skill_name].get("instructions", "")
            }

        return {"success": False, "error": f"Skill not found: {skill_name}"}

    def _handle_find_skills(self, data: Dict) -> Dict:
        """Find relevant skills for a query"""
        query = data.get("query", "")

        if not query:
            return {"success": False, "error": "query is required"}

        if SKILLS_LOADER_AVAILABLE:
            try:
                skills = find_skills_func(query)
                return {
                    "success": True,
                    "query": query,
                    "skills": skills,
                    "count": len(skills)
                }
            except Exception as e:
                return {"success": False, "error": f"Skills search error: {e}"}

        # Simple fallback search
        query_lower = query.lower()
        matches = []
        for name, skill in self.skills.items():
            desc = skill.get("description", "").lower()
            if query_lower in name.lower() or query_lower in desc:
                matches.append({
                    "name": name,
                    "description": skill.get("description", "")
                })

        return {
            "success": True,
            "query": query,
            "skills": matches,
            "count": len(matches)
        }

    def _handle_blueprint_intelligence(self, data: Dict) -> Dict:
        """Handle Blueprint Intelligence commands"""
        try:
            from blueprint_intelligence import handle_command
            return handle_command(data)
        except ImportError:
            return {"success": False, "error": "Blueprint Intelligence module not loaded"}

    def _handle_viewport_command(self, data: Dict) -> Dict:
        """Route viewport commands to ops/viewport.py"""
        try:
            from ops.viewport import handle_viewport_command
            return handle_viewport_command(data)
        except ImportError:
            return {"success": False, "error": "Viewport ops module not loaded"}

    def _handle_organization_command(self, data: Dict) -> Dict:
        """Route organization commands to ops/organization.py"""
        try:
            from ops.organization import handle_organization_command
            return handle_organization_command(data)
        except ImportError:
            return {"success": False, "error": "Organization ops module not loaded"}

    def _handle_blueprint_connection_command(self, data: Dict) -> Dict:
        """Route blueprint connection commands to ops/blueprint_connections.py"""
        try:
            from ops.blueprint_connections import handle_blueprint_connection_command
            return handle_blueprint_connection_command(data)
        except ImportError:
            return {"success": False, "error": "Blueprint connections ops module not loaded"}

    def _handle_material_command(self, data: Dict) -> Dict:
        """Route material commands to ops/material.py"""
        try:
            from ops.material import handle_material_command
            return handle_material_command(data)
        except ImportError:
            return {"success": False, "error": "Material ops module not loaded"}

    def _handle_validation_command(self, data: Dict) -> Dict:
        """Route validation commands to ops/validation.py"""
        try:
            from ops.validation import handle_validation_command
            return handle_validation_command(data)
        except ImportError:
            return {"success": False, "error": "Validation ops module not loaded"}

    def _handle_physics_command(self, data: Dict) -> Dict:
        """Route physics commands to ops/physics.py"""
        try:
            from ops.physics import handle_physics_command
            return handle_physics_command(data)
        except ImportError:
            return {"success": False, "error": "Physics ops module not loaded"}

    def _handle_get_selected_assets(self, data: Dict) -> Dict:
        """Get currently selected assets in Content Browser OR actors in viewport"""
        try:
            import unreal

            assets = []
            source = "none"

            # First try: Content Browser selection
            try:
                utility = unreal.EditorUtilityLibrary()
                selected_assets = utility.get_selected_assets()

                for asset in selected_assets:
                    asset_data = {
                        "name": asset.get_name(),
                        "type": asset.get_class().get_name(),
                        "path": asset.get_path_name()
                    }
                    assets.append(asset_data)

                if assets:
                    source = "content_browser"
            except Exception:
                pass

            # Second try: Viewport/Outliner selection (actors)
            if not assets:
                try:
                    selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()

                    for actor in selected_actors:
                        # Get actor info
                        actor_data = {
                            "name": actor.get_actor_label(),
                            "type": actor.get_class().get_name(),
                            "path": actor.get_path_name()
                        }

                        # Try to get the associated static mesh asset if applicable
                        if hasattr(actor, 'static_mesh_component'):
                            try:
                                smc = actor.static_mesh_component
                                if smc and smc.static_mesh:
                                    actor_data["mesh_asset"] = smc.static_mesh.get_path_name()
                            except (AttributeError, RuntimeError):
                                pass

                        # Get location for context
                        try:
                            loc = actor.get_actor_location()
                            actor_data["location"] = {"x": loc.x, "y": loc.y, "z": loc.z}
                        except (AttributeError, RuntimeError):
                            pass

                        assets.append(actor_data)

                    if assets:
                        source = "viewport"
                except Exception:
                    pass

            return {
                "success": True,
                "assets": assets,
                "selected_count": len(assets),
                "source": source,
                "message": f"Found {len(assets)} selected item(s) from {source}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get selected assets: {e}",
                "traceback": traceback.format_exc()
            }

    def _handle_get_selected_actors(self, data: Dict) -> Dict:
        """Get currently selected actors in viewport/outliner"""
        try:
            import unreal

            # Get selected actors
            selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()

            include_details = data.get("include_details", True)

            actors = []
            for actor in selected_actors:
                if include_details:
                    loc = actor.get_actor_location()
                    rot = actor.get_actor_rotation()
                    scale = actor.get_actor_scale3d()

                    actor_data = {
                        "name": actor.get_actor_label(),
                        "class": actor.get_class().get_name(),
                        "location": [loc.x, loc.y, loc.z],
                        "rotation": [rot.pitch, rot.yaw, rot.roll],
                        "scale": [scale.x, scale.y, scale.z]
                    }
                else:
                    actor_data = {
                        "name": actor.get_actor_label(),
                        "class": actor.get_class().get_name()
                    }
                actors.append(actor_data)

            return {
                "success": True,
                "actors": actors,
                "selected_count": len(actors),
                "message": f"Found {len(actors)} selected actor(s)"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get selected actors: {e}",
                "traceback": traceback.format_exc()
            }

    def _handle_execute_function(self, data: Dict) -> Dict:
        """Route execute_function calls to appropriate handlers.

        Note: This handler is already executing on the main thread (if needed),
        so we call the target handler directly without another main thread dispatch.
        """
        function_name = data.get("function_name", "")
        parameters = data.get("parameters", {})

        if not function_name:
            return {
                "success": False,
                "error": "function_name is required",
                "available_functions": list(self.handlers.keys())
            }

        # Merge parameters into data and set type to function_name
        routed_data = {**parameters, "type": function_name, "_client_ip": data.get("_client_ip", "unknown")}

        # Find and execute the handler directly (we're already on main thread)
        handler = self.handlers.get(function_name)
        if handler:
            # Call handler directly - execute_function already ran on main thread
            return handler(routed_data)
        else:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}",
                "available_functions": list(self.handlers.keys())
            }


# Global server instance
_server_instance: Optional[KarianaSocketServer] = None


def get_server() -> Optional[KarianaSocketServer]:
    """Get the global server instance"""
    return _server_instance


def start_server(
    host: str = "localhost",
    port: int = 9877,
    require_auth: bool = False,
    auto_port: bool = True
) -> KarianaSocketServer:
    """
    Start the socket server with automatic instance management.

    Args:
        host: Host to bind to
        port: Port to bind to (may be auto-allocated if auto_port=True)
        require_auth: Whether to require token authentication
        auto_port: Auto-allocate port if default is in use

    Returns:
        KarianaSocketServer instance
    """
    global _server_instance

    if _server_instance is None:
        _server_instance = KarianaSocketServer(host, port, require_auth)
        _server_instance.start()

        # Log connection info
        if _server_instance.instance_manager:
            logger.info("Server Ready:")
            logger.info(f"  Port: {_server_instance.port}")
            logger.info(f"  Instance: {_server_instance.instance_manager.instance_id[:20]}...")
            logger.debug(f"  Token: {_server_instance.instance_manager.token[:8]}...")
            logger.info(f"  Auth Required: {require_auth}")

    return _server_instance


def discover_servers() -> list:
    """
    Discover all running KarianaUMCP servers.

    Returns:
        List of discovered server info dicts
    """
    if INSTANCE_MANAGER_AVAILABLE:
        manager = get_instance_manager()
        return manager.discover_instances()
    return []


def get_server_token() -> Optional[str]:
    """
    Get the current server's authentication token.

    Returns:
        Token string or None if no server running
    """
    if _server_instance and _server_instance.instance_manager:
        return _server_instance.instance_manager.token
    return None


def stop_server():
    """Stop the socket server and unregister the instance"""
    global _server_instance

    if _server_instance:
        # Unregister instance
        if _server_instance.instance_manager:
            _server_instance.instance_manager.unregister_instance()
            logger.info("Instance unregistered")

        _server_instance.stop()
        _server_instance = None


# Export all public functions
__all__ = [
    'KarianaSocketServer',
    'get_server',
    'start_server',
    'stop_server',
    'discover_servers',
    'get_server_token',
]


# Auto-start when imported in Unreal
if __name__ != "__main__":
    try:
        import unreal
        start_server()
    except ImportError:
        pass  # Not running in Unreal
