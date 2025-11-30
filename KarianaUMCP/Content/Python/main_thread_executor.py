"""
Main Thread Executor for KarianaUMCP
====================================
Ensures Unreal API calls run on the main game thread.

Usage:
    from main_thread_executor import execute_on_main_thread
    result = execute_on_main_thread(lambda: unreal.EditorLevelLibrary.get_editor_world())
"""

import queue
import threading
import time
from typing import Any, Callable, Optional

from logger import get_logger

logger = get_logger("main_thread")

# Command queue and results
_command_queue = queue.Queue()
_results = {}
_result_lock = threading.Lock()
_callback_registered = False
_command_counter = 0
_counter_lock = threading.Lock()


def _get_next_id():
    """Get unique command ID"""
    global _command_counter
    with _counter_lock:
        _command_counter += 1
        return _command_counter


def _process_queue():
    """Process queued commands on main thread - called by Unreal tick"""
    try:
        while not _command_queue.empty():
            try:
                cmd_id, func = _command_queue.get_nowait()
                try:
                    result = func()
                    with _result_lock:
                        _results[cmd_id] = {"success": True, "result": result}
                except Exception as e:
                    import traceback
                    with _result_lock:
                        _results[cmd_id] = {
                            "success": False,
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        }
            except queue.Empty:
                break
    except Exception as e:
        logger.error(f"Queue processor error: {e}")


def _register_tick_callback() -> bool:
    """
    Register the tick callback with Unreal.

    IMPORTANT: This MUST be called from the main thread (during init_unreal.py).
    Calling from a background thread will crash Unreal.
    """
    global _callback_registered
    if _callback_registered:
        return True

    try:
        import unreal

        # Define the tick callback
        def tick_callback(delta_time):
            _process_queue()

        # Register with Unreal's slate system
        # This will crash if not on main thread - that's expected
        unreal.register_slate_post_tick_callback(tick_callback)
        _callback_registered = True
        logger.info("Main thread executor registered successfully")
        return True

    except ImportError:
        logger.debug("Not in Unreal environment")
        return False
    except RuntimeError as e:
        # This will happen if called from background thread
        logger.debug(f"Tick callback registration failed: {e}")
        logger.debug("(This is normal if called from background thread)")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error registering tick callback: {e}")
        return False


def execute_on_main_thread(func: Callable, timeout: float = 10.0) -> Any:
    """
    Execute a function on Unreal's main thread and wait for result.

    Args:
        func: Function to execute (no arguments)
        timeout: Max seconds to wait for result

    Returns:
        Result from function or raises exception
    """
    # Ensure callback is registered
    if not _callback_registered:
        _register_tick_callback()

    # If not in Unreal or callback failed, try direct execution
    if not _callback_registered:
        return func()

    # Queue the command
    cmd_id = _get_next_id()
    _command_queue.put((cmd_id, func))

    # Wait for result
    start_time = time.time()
    while time.time() - start_time < timeout:
        with _result_lock:
            if cmd_id in _results:
                result = _results.pop(cmd_id)
                if result["success"]:
                    return result["result"]
                else:
                    raise RuntimeError(f"{result['error']}\n{result.get('traceback', '')}")
        time.sleep(0.01)  # 10ms polling

    raise TimeoutError(f"Command timed out after {timeout}s")


def is_main_thread() -> bool:
    """Check if current thread is likely the main thread"""
    try:
        import unreal
        # If we can call simple unreal functions, we're probably on main thread
        # This is a heuristic, not guaranteed
        return True
    except ImportError:
        return False
    except Exception:
        return False


# NOTE: Registration happens in init_unreal.py which runs on the main thread.
# Do NOT auto-register here as this module may be imported from background threads.
