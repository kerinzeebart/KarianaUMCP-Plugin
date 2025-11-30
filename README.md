# KarianaUMCP Plugin v1.1.0

**AI-Powered Virtual Production Control for Unreal Engine 5.6+**

MCP 1st Birthday Hackathon Submission | Track: MCP in Action

## What's New in v1.1.0

### Bug Fixes & Improvements
- **Centralized Logging**: New `logger.py` module with stderr output for MCP stdio compatibility
- **Structured Error Responses**: New `errors.py` with MCP-compliant error codes (-32xxx)
- **Input Validation**: New `validators.py` with enum constants and validation functions
- **Fixed Exception Handling**: Replaced bare `except:` blocks with specific exception types
- **Improved Socket Server**: Better connection handling and error reporting

### Files Changed
- `logger.py` (NEW) - Centralized logging to stderr
- `errors.py` (NEW) - Structured MCP error responses
- `validators.py` (NEW) - Input validation utilities
- `init_unreal.py` - Fixed 11 print statements
- `main_thread_executor.py` - Fixed prints + bare except
- `instance_manager.py` - Fixed prints + 6 bare excepts
- `socket_server.py` - Fixed 15 prints + 4 bare excepts
- `ops/blueprint.py` - Fixed 4 bare excepts

## Installation

1. Copy the `KarianaUMCP` folder to your Unreal Engine project's `Plugins` directory
2. Enable the plugin in your project settings
3. Restart Unreal Editor

## Quick Start

1. Open your Unreal Engine project
2. Look for the 4-digit PIN in the Output Log
3. Connect via the Gradio UI or Claude Desktop

## Features

- **40+ MCP Tools** for Unreal Engine control
- **PIN-Based Authentication** - Simple, secure connection
- **Multi-Instance Support** - Control multiple UE instances
- **Claude Skills Integration** - 8 specialized AI agents
- **Real-time Monitoring** - FPS, logs, connection status

## Links

- **Demo**: [HuggingFace Space](https://huggingface.co/spaces/barlowski/KarianaUMCP)
- **Website**: [kariana.base44.app](https://kariana.base44.app)
- **Video**: [YouTube Demo](https://www.youtube.com/watch?v=Xe_UNMfnqUQ)

## Requirements

- Unreal Engine 5.6+
- Python 3.10+
- Gradio 5.9.0+ (for UI)

## License

MIT License

---

*MCP 1st Birthday Hackathon 2025*
