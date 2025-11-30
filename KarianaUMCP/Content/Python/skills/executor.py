"""
KarianaUMCP Skills Executor
===========================
Execute skill workflows step by step.
"""

import json
import socket
import traceback
from typing import Dict, Any, List, Optional, Callable


class SkillExecutor:
    """Execute skills step by step"""

    def __init__(self, socket_host: str = "localhost", socket_port: int = 9877):
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.context: Dict[str, Any] = {}  # Stores outputs from previous steps
        self.progress_callback: Optional[Callable] = None

    def execute(self, skill: Dict, parameters: Dict = None) -> Dict[str, Any]:
        """
        Execute a skill.

        Args:
            skill: Skill manifest dictionary
            parameters: Input parameters for the skill

        Returns:
            dict: Execution results
        """
        parameters = parameters or {}
        self.context = {"input": parameters}

        skill_name = skill.get("name", "Unknown")
        steps = skill.get("steps", [])
        required_params = skill.get("parameters", {})

        # Validate required parameters
        for param_name, param_info in required_params.items():
            if param_info.get("required", False) and param_name not in parameters:
                return {
                    "success": False,
                    "error": f"Missing required parameter: {param_name}",
                    "skill": skill_name
                }

        results = {
            "success": True,
            "skill": skill_name,
            "steps_executed": 0,
            "steps_total": len(steps),
            "step_results": [],
            "context": {}
        }

        # Execute each step
        for i, step in enumerate(steps):
            step_name = step.get("name", f"Step {i+1}")
            action = step.get("action")

            self._report_progress(skill_name, i + 1, len(steps), step_name)

            try:
                step_result = self._execute_step(step, i)

                results["step_results"].append({
                    "step": i + 1,
                    "name": step_name,
                    "action": action,
                    "success": step_result.get("success", False),
                    "result": step_result
                })

                results["steps_executed"] = i + 1

                # Stop if step failed and skill doesn't allow continuation
                if not step_result.get("success", False):
                    if not skill.get("continue_on_error", False):
                        results["success"] = False
                        results["error"] = f"Step {i+1} failed: {step_result.get('error', 'Unknown error')}"
                        break

            except Exception as e:
                results["success"] = False
                results["error"] = f"Step {i+1} exception: {str(e)}"
                results["step_results"].append({
                    "step": i + 1,
                    "name": step_name,
                    "action": action,
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                break

        # Include final context
        results["context"] = self.context

        return results

    def _execute_step(self, step: Dict, step_index: int) -> Dict[str, Any]:
        """Execute a single step"""
        action = step.get("action")
        if not action:
            return {"success": False, "error": "Step missing 'action' field"}

        # Build parameters for this step
        params = {}

        # Get explicit parameters
        if "parameters" in step:
            params.update(step["parameters"])

        # Resolve input references (e.g., "$context.actors")
        if "input" in step:
            input_ref = step["input"]
            if isinstance(input_ref, str) and input_ref.startswith("$"):
                # Resolve context reference
                value = self._resolve_reference(input_ref)
                if value is not None:
                    # Merge into params based on action type
                    if isinstance(value, dict):
                        params.update(value)
                    else:
                        params["input"] = value

        # Execute the action via socket server
        message = {"type": action, **params}
        result = self._send_to_socket(message)

        # Store output in context if specified
        if "output" in step and result.get("success", False):
            output_name = step["output"]
            self.context[output_name] = result

        return result

    def _resolve_reference(self, ref: str) -> Any:
        """Resolve a context reference like $context.actors"""
        if not ref.startswith("$"):
            return ref

        parts = ref[1:].split(".")
        value = self.context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _send_to_socket(self, message: Dict) -> Dict:
        """Send message to socket server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((self.socket_host, self.socket_port))

            sock.send((json.dumps(message) + '\n').encode('utf-8'))

            response_data = ""
            while True:
                chunk = sock.recv(4096).decode('utf-8')
                if not chunk:
                    break
                response_data += chunk
                if '\n' in response_data:
                    break

            sock.close()

            if response_data.strip():
                return json.loads(response_data.strip().split('\n')[0])
            else:
                return {"success": False, "error": "Empty response"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _report_progress(self, skill: str, step: int, total: int, name: str):
        """Report progress if callback is set"""
        if self.progress_callback:
            self.progress_callback({
                "skill": skill,
                "step": step,
                "total": total,
                "step_name": name,
                "progress": step / total * 100
            })
        else:
            print(f"  [{step}/{total}] {name}")


def execute_skill(skill: Dict, parameters: Dict = None) -> Dict[str, Any]:
    """
    Execute a skill.

    Args:
        skill: Skill manifest dictionary
        parameters: Input parameters

    Returns:
        dict: Execution results
    """
    executor = SkillExecutor()
    return executor.execute(skill, parameters)


def execute_skill_by_name(skill_name: str, parameters: Dict = None) -> Dict[str, Any]:
    """
    Execute a skill by name.

    Args:
        skill_name: Name of the skill to execute
        parameters: Input parameters

    Returns:
        dict: Execution results
    """
    from skills.loader import load_skill

    skill = load_skill(skill_name)
    if not skill:
        return {
            "success": False,
            "error": f"Skill not found: {skill_name}"
        }

    return execute_skill(skill, parameters)
