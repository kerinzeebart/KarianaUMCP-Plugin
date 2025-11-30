"""
KarianaUMCP One-Click Installer
===============================
Automated setup script for the KarianaUMCP plugin.

This installer:
1. Checks prerequisites (Python, pip, Unreal version)
2. Installs Python dependencies (gradio, pillow, pyngrok, etc.)
3. Configures Unreal Engine settings
4. Starts all services
5. Verifies the installation

Usage:
    In Unreal Python console:
    >>> import sys
    >>> sys.path.append('/path/to/KarianaUMCP/Content/Python')
    >>> import installer
    >>> installer.install_and_setup()
"""

import os
import sys
import subprocess
import json
import socket
import time
from typing import Dict, Any, List, Optional


class KarianaInstaller:
    """One-click installer for KarianaUMCP"""

    def __init__(self):
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.results = {
            "prerequisites": {},
            "dependencies": {},
            "configuration": {},
            "services": {},
            "verification": {}
        }

    def install_and_setup(self, start_ngrok: bool = True) -> Dict[str, Any]:
        """
        Complete installation and setup process.

        Args:
            start_ngrok: Whether to start ngrok tunnel (default True)

        Returns:
            dict: Installation results and status
        """
        print("=" * 60)
        print("KarianaUMCP One-Click Installer")
        print("=" * 60)
        print()

        # Step 1: Check prerequisites
        print("Step 1: Checking prerequisites...")
        self._check_prerequisites()

        # Step 2: Install Python dependencies
        print("\nStep 2: Installing Python dependencies...")
        self._install_dependencies()

        # Step 3: Configure Unreal Engine
        print("\nStep 3: Configuring Unreal Engine...")
        self._configure_unreal()

        # Step 4: Start services
        print("\nStep 4: Starting services...")
        self._start_services(start_ngrok)

        # Step 5: Verify installation
        print("\nStep 5: Verifying installation...")
        self._verify_installation()

        # Print summary
        self._print_summary()

        return self.results

    def _check_prerequisites(self):
        """Check system prerequisites"""
        prereqs = {}

        # Check Python version
        python_version = sys.version_info
        prereqs["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
        prereqs["python_ok"] = python_version >= (3, 9)

        if prereqs["python_ok"]:
            print(f"  [OK] Python {prereqs['python_version']}")
        else:
            print(f"  [WARN] Python {prereqs['python_version']} (3.9+ recommended)")

        # Check pip
        try:
            import pip
            prereqs["pip_ok"] = True
            prereqs["pip_version"] = pip.__version__
            print(f"  [OK] pip {prereqs['pip_version']}")
        except ImportError:
            prereqs["pip_ok"] = False
            print("  [FAIL] pip not available")

        # Check if running in Unreal
        try:
            import unreal
            prereqs["unreal_ok"] = True
            prereqs["unreal_version"] = unreal.SystemLibrary.get_engine_version()
            print(f"  [OK] Unreal Engine {prereqs['unreal_version']}")
        except ImportError:
            prereqs["unreal_ok"] = False
            print("  [WARN] Not running in Unreal Engine")

        self.results["prerequisites"] = prereqs

    def _install_dependencies(self):
        """Install required Python packages"""
        dependencies = {
            "pillow": "PIL image processing",
            "pyngrok": "ngrok tunnel support",
            "requests": "HTTP requests",
        }

        # Optional dependencies (don't fail if these don't install)
        optional_deps = {
            "gradio": "Web UI dashboard",
        }

        installed = {}
        failed = {}

        for package, description in dependencies.items():
            success = self._install_package(package)
            if success:
                installed[package] = description
                print(f"  [OK] {package} - {description}")
            else:
                failed[package] = description
                print(f"  [FAIL] {package} - {description}")

        for package, description in optional_deps.items():
            success = self._install_package(package)
            if success:
                installed[package] = description
                print(f"  [OK] {package} - {description}")
            else:
                print(f"  [SKIP] {package} - {description} (optional)")

        self.results["dependencies"] = {
            "installed": installed,
            "failed": failed
        }

    def _install_package(self, package: str) -> bool:
        """Install a single package"""
        try:
            # Try import first
            __import__(package.replace("-", "_").split("[")[0])
            return True
        except ImportError:
            pass

        # Try pip install
        try:
            # Use Unreal's Python if available
            try:
                import unreal
                cmd = f"py pip install {package}"
                unreal.SystemLibrary.execute_console_command(None, cmd)
                time.sleep(2)  # Give pip time to complete

                # Verify installation
                try:
                    __import__(package.replace("-", "_").split("[")[0])
                    return True
                except ImportError:
                    pass
            except:
                pass

            # Fallback to subprocess
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ])
            return True

        except Exception as e:
            return False

    def _configure_unreal(self):
        """Configure Unreal Engine settings"""
        config = {}

        try:
            import unreal

            project_dir = str(unreal.Paths.project_dir())
            config_dir = os.path.join(project_dir, "Config")

            # Path to DefaultEngine.ini
            engine_ini = os.path.join(config_dir, "DefaultEngine.ini")

            # Python settings to add
            python_settings = """
[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution=True
bAllowRemotePythonExecution=True
"""

            # Check if settings already exist
            if os.path.exists(engine_ini):
                with open(engine_ini, 'r') as f:
                    content = f.read()

                if "PythonScriptPluginSettings" not in content:
                    # Append settings
                    with open(engine_ini, 'a') as f:
                        f.write(python_settings)
                    config["engine_ini_updated"] = True
                    print("  [OK] Updated DefaultEngine.ini")
                else:
                    config["engine_ini_updated"] = False
                    print("  [OK] DefaultEngine.ini already configured")
            else:
                print("  [WARN] DefaultEngine.ini not found")

            config["project_dir"] = project_dir
            config["success"] = True

        except ImportError:
            config["success"] = False
            print("  [SKIP] Not running in Unreal Engine")

        self.results["configuration"] = config

    def _start_services(self, start_ngrok: bool = True):
        """Start KarianaUMCP services"""
        services = {}

        # Start socket server
        try:
            from socket_server import start_server, get_server
            server = start_server()

            if server and server.running:
                services["socket_server"] = {
                    "status": "running",
                    "port": 9877
                }
                print("  [OK] Socket server started (port 9877)")
            else:
                services["socket_server"] = {"status": "failed"}
                print("  [FAIL] Socket server failed to start")

        except Exception as e:
            services["socket_server"] = {"status": "error", "error": str(e)}
            print(f"  [FAIL] Socket server error: {e}")

        # Start HTTP proxy
        try:
            from ngrok_proxy import start_proxy, get_proxy
            proxy = start_proxy(start_ngrok=False)

            if proxy and proxy.running:
                services["http_proxy"] = {
                    "status": "running",
                    "port": 8765
                }
                print("  [OK] HTTP proxy started (port 8765)")

                # Start ngrok if requested
                if start_ngrok:
                    ngrok_url = proxy.start_ngrok()
                    if ngrok_url:
                        services["ngrok"] = {
                            "status": "running",
                            "url": ngrok_url
                        }
                        print(f"  [OK] ngrok tunnel: {ngrok_url}")
                    else:
                        services["ngrok"] = {"status": "not_started"}
                        print("  [SKIP] ngrok not started (pyngrok may not be installed)")

            else:
                services["http_proxy"] = {"status": "failed"}
                print("  [FAIL] HTTP proxy failed to start")

        except Exception as e:
            services["http_proxy"] = {"status": "error", "error": str(e)}
            print(f"  [FAIL] HTTP proxy error: {e}")

        self.results["services"] = services

    def _verify_installation(self):
        """Verify the installation is working"""
        verification = {}

        # Test socket connection
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 9877))
            sock.close()

            if result == 0:
                verification["socket_connection"] = True
                print("  [OK] Socket server reachable")
            else:
                verification["socket_connection"] = False
                print("  [FAIL] Socket server not reachable")

        except Exception as e:
            verification["socket_connection"] = False
            print(f"  [FAIL] Socket test error: {e}")

        # Test ping command
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', 9877))
            sock.send(b'{"type": "ping"}\n')
            response = sock.recv(4096).decode('utf-8')
            sock.close()

            if "pong" in response:
                verification["ping_test"] = True
                print("  [OK] Ping test passed")
            else:
                verification["ping_test"] = False
                print("  [FAIL] Ping test failed")

        except Exception as e:
            verification["ping_test"] = False
            print(f"  [FAIL] Ping test error: {e}")

        # Test list_functions
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', 9877))
            sock.send(b'{"type": "list_functions"}\n')
            response = sock.recv(8192).decode('utf-8')
            sock.close()

            data = json.loads(response.strip())
            if data.get("success") and "functions" in data:
                verification["list_functions"] = True
                verification["function_count"] = data.get("count", 0)
                print(f"  [OK] Found {verification['function_count']} functions")
            else:
                verification["list_functions"] = False
                print("  [FAIL] list_functions failed")

        except Exception as e:
            verification["list_functions"] = False
            print(f"  [FAIL] list_functions error: {e}")

        self.results["verification"] = verification

    def _print_summary(self):
        """Print installation summary"""
        print()
        print("=" * 60)
        print("Installation Summary")
        print("=" * 60)

        # Check overall success
        all_ok = True

        if not self.results["prerequisites"].get("python_ok", False):
            all_ok = False

        if self.results["dependencies"].get("failed"):
            all_ok = False

        if self.results["services"].get("socket_server", {}).get("status") != "running":
            all_ok = False

        if not self.results["verification"].get("ping_test", False):
            all_ok = False

        if all_ok:
            print()
            print("SUCCESS! KarianaUMCP is installed and running.")
            print()

            # Print connection info
            ngrok_url = self.results["services"].get("ngrok", {}).get("url")

            print("Next Steps:")
            print("-" * 40)
            print()
            print("1. Add to Claude Desktop config:")
            print()
            print('   "kariana": {')
            print('     "command": "node",')
            print('     "args": ["/path/to/kariana-mcp-bridge.js"],')
            print('     "env": {')

            if ngrok_url:
                print(f'       "KARIANA_URL": "{ngrok_url}"')
            else:
                print('       "KARIANA_URL": "http://localhost:8765"')

            print('     }')
            print('   }')
            print()
            print("2. Restart Claude Desktop")
            print()
            print('3. Test with: "List all actors in my Unreal level"')
            print()

        else:
            print()
            print("PARTIAL SUCCESS - Some components may not be working.")
            print()
            print("Check the results above for details.")
            print("Common fixes:")
            print("  - Restart Unreal Engine")
            print("  - Enable Python Script Plugin")
            print("  - Check port 9877 is not in use")
            print()

        print("=" * 60)


def install_and_setup(start_ngrok: bool = True) -> Dict[str, Any]:
    """
    One-click installation function.

    Args:
        start_ngrok: Whether to start ngrok tunnel (default True)

    Returns:
        dict: Installation results
    """
    installer = KarianaInstaller()
    return installer.install_and_setup(start_ngrok)


def quick_start():
    """Quick start - minimal setup without ngrok"""
    installer = KarianaInstaller()
    return installer.install_and_setup(start_ngrok=False)


def verify_installation() -> Dict[str, Any]:
    """Verify existing installation"""
    installer = KarianaInstaller()
    print("Verifying KarianaUMCP installation...")
    installer._verify_installation()
    return installer.results["verification"]


# Convenience function for Unreal console
def setup():
    """Alias for install_and_setup"""
    return install_and_setup()


if __name__ == "__main__":
    install_and_setup()
