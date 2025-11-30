# KarianaUMCP Skills Guide

Complete guide to using and creating skills for KarianaUMCP - the Unreal Engine integration for Claude AI.

## Table of Contents

1. [What Are Skills?](#what-are-skills)
2. [Getting Started](#getting-started)
3. [Using Skills in Gradio Dashboard](#using-skills-in-gradio-dashboard)
4. [Available Skills](#available-skills)
5. [Creating Custom Skills](#creating-custom-skills)
6. [Skills API](#skills-api)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What Are Skills?

**Skills** teach Claude AI how to perform tasks in a repeatable way. They are specialized folders containing:

- **SKILL.md** - Main instruction file with YAML frontmatter
- **scripts/** - Optional executable Python scripts
- **resources/** - Optional supporting files (templates, configs)

### Progressive Disclosure Architecture

Skills use a token-efficient loading system:

| Phase | Tokens | What Loads |
|-------|--------|------------|
| 1. Discovery | ~100 | Skill name + description only |
| 2. Instructions | <5k | Full SKILL.md instructions |
| 3. Resources | As needed | Scripts and files |

This means multiple skills remain available without overwhelming Claude's context.

---

## Getting Started

### Prerequisites

- KarianaUMCP plugin installed in Unreal Engine
- Socket server running (port 9877)
- Python 3.9+ with Gradio installed

### Quick Start

1. **Start the Socket Server**
   ```
   Open your Unreal project with KarianaUMCP plugin enabled
   The socket server starts automatically on port 9877
   ```

2. **Launch Gradio Dashboard**
   ```bash
   cd Plugins/KarianaUMCP
   python -m gradio_dashboard
   ```

3. **Navigate to Skills Tab**
   - Open http://localhost:7860 in your browser
   - Click on the "Skills" tab
   - Browse available skills

---

## Using Skills in Gradio Dashboard

### Skills Browser Tab

The dashboard provides a visual interface for skills:

```
┌────────────────────────────────────────────────────┐
│  KarianaUMCP Dashboard                              │
├────────────────────────────────────────────────────┤
│  [Status] [Tools] [Skills] [Logs]                  │
├────────────────────────────────────────────────────┤
│                                                     │
│  Available Skills                                   │
│  ┌──────────────┬───────────────────────────────┐ │
│  │ spawn-actor  │ Spawn actors in Unreal levels │ │
│  │ screenshot   │ Capture viewport screenshots  │ │
│  │ blueprint-   │ Create Blueprints from code   │ │
│  │   helper     │                               │ │
│  │ level-       │ Organize World Outliner       │ │
│  │   organizer  │                               │ │
│  └──────────────┴───────────────────────────────┘ │
│                                                     │
│  [Load Skill] [Refresh] [Create New]               │
└────────────────────────────────────────────────────┘
```

### Loading a Skill

1. Select a skill from the list
2. Click "Load Skill" to view full instructions
3. The skill's documentation appears with:
   - Usage examples
   - Parameter reference
   - Copy-ready code snippets

### Executing Skill Actions

Skills integrate with the Tool Execution panel:

1. Go to **Tools** tab
2. Select tool category (e.g., "Actor Tools")
3. The loaded skill provides context for parameter values
4. Execute and view results

---

## Available Skills

### spawn-actor

Spawn and manipulate actors in Unreal Engine levels.

**Key Actions:**
- Spawn primitives (Cube, Sphere, Cylinder)
- Spawn Blueprint actors
- Set transforms and materials
- Enable physics

**Example:**
```python
spawn_actor(
    actor_type="Cube",
    location=[0, 0, 100],
    scale=[2, 2, 2],
    simulate_physics=True
)
```

### screenshot

Capture high-quality screenshots from the Unreal viewport.

**Key Actions:**
- Capture current viewport
- Set custom resolution
- Multiple formats (PNG, JPEG, WebP)
- Capture from specific cameras

**Example:**
```python
take_screenshot(
    width=1920,
    height=1080,
    format="png"
)
```

### blueprint-helper

Create and modify Unreal Blueprints programmatically.

**Key Actions:**
- Create Blueprint classes
- Add components
- Set default properties
- Convert actors to Blueprints

**Example:**
```python
create_blueprint(
    name="BP_CustomActor",
    parent_class="Actor",
    save_path="/Game/Blueprints"
)
```

### level-organizer

Organize actors in the World Outliner with smart hierarchies.

**Key Actions:**
- Create folder structures
- Move actors to folders
- Batch rename actors
- Auto-organize by type

**Example:**
```python
auto_organize_level()
```

---

## Creating Custom Skills

### Directory Structure

```
my-skill/
├── SKILL.md          # Required: Main instruction file
├── scripts/          # Optional: Python scripts
│   └── helper.py
└── resources/        # Optional: Templates, configs
    └── template.json
```

### SKILL.md Template

```yaml
---
name: my-custom-skill
description: Brief description for skill discovery (keep concise)
version: 1.0.0
author: Your Name
dependencies:
  - unreal
  - pillow
---

# My Custom Skill

Detailed instructions that Claude reads when the skill is activated.

## Capabilities

- Capability 1
- Capability 2
- Capability 3

## Usage

### Basic Example

```python
my_function(param1="value")
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| param1 | string | Yes | Description |
| param2 | int | No | Description (default: 10) |

## Examples

### Example 1: Simple Use Case

```python
# Code example with comments
```

## Error Handling

- Common error 1 and solution
- Common error 2 and solution

## Related Skills

- `related-skill-1` - Description
- `related-skill-2` - Description
```

### Adding Scripts

Create executable scripts in the `scripts/` directory:

```python
# scripts/helper.py
"""Helper script for my-custom-skill"""

def process_data(data: dict) -> dict:
    """Process input data and return result."""
    # Implementation
    return {"processed": True, "data": data}

if __name__ == "__main__":
    import json
    import sys

    input_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    result = process_data(input_data)
    print(json.dumps(result))
```

### Installing Your Skill

1. Copy your skill folder to:
   ```
   Plugins/KarianaUMCP/skills/your-skill-name/
   ```

2. Refresh the skills list in the dashboard

3. Your skill appears in the browser

---

## Skills API

### Socket Server Endpoints

Skills integrate with the socket server via these message types:

#### Discover Skills
```json
{"type": "discover_skills"}
```

Response:
```json
{
  "success": true,
  "skills": [
    {
      "name": "spawn-actor",
      "description": "Spawn actors in Unreal Engine levels",
      "version": "1.0.0"
    }
  ]
}
```

#### Load Skill
```json
{"type": "load_skill", "skill_name": "spawn-actor"}
```

Response:
```json
{
  "success": true,
  "name": "spawn-actor",
  "instructions": "# Spawn Actor Skill\n\n...",
  "has_scripts": true
}
```

#### Find Relevant Skills
```json
{"type": "find_skills", "query": "how to spawn a cube"}
```

Response:
```json
{
  "success": true,
  "skills": [
    {"name": "spawn-actor", "description": "..."}
  ]
}
```

### Python API

Use the skills loader in Python code:

```python
from skills_loader import get_skills_loader, discover_skills, load_skill

# Discover all skills
skills = discover_skills()
for skill in skills:
    print(f"{skill['name']}: {skill['description']}")

# Load specific skill
skill = load_skill("spawn-actor")
print(skill['instructions'])

# Find relevant skills
from skills_loader import find_skills
relevant = find_skills("create actor with physics")
```

---

## Best Practices

### Writing Good Skills

1. **Keep descriptions concise** - Used for discovery matching
2. **Use clear, actionable instructions** - Write as if for a collaborator
3. **Include practical examples** - Show real code, not pseudocode
4. **Document all parameters** - Type, required status, defaults
5. **Version your skills** - Semantic versioning (1.0.0)
6. **List dependencies** - What packages/plugins are needed
7. **Test thoroughly** - Verify across different scenarios

### Skill Organization

```
skills/
├── core/              # Essential skills
│   ├── spawn-actor/
│   ├── screenshot/
│   └── blueprint-helper/
├── workflow/          # Multi-step workflows
│   ├── level-setup/
│   └── asset-pipeline/
└── custom/            # User-created skills
    └── my-project-skill/
```

### Security Considerations

- **Only install skills from trusted sources**
- Review SKILL.md and scripts before enabling
- Be cautious with skills that request file system access
- Audit skills before production deployment

---

## Troubleshooting

### Skills Not Appearing

1. Verify skill directory structure
2. Check SKILL.md has valid YAML frontmatter
3. Ensure `name` and `description` fields exist
4. Restart the Gradio dashboard

### Skill Not Loading

1. Check socket server is running (port 9877)
2. Verify file encoding is UTF-8
3. Check for YAML syntax errors in frontmatter
4. Review server logs for error messages

### Script Execution Failures

1. Verify Python dependencies installed
2. Check script has correct shebang
3. Test script independently first
4. Review Unreal Output Log for Python errors

### Getting Help

- Check the [KarianaUMCP GitHub Issues](https://github.com/kariana-ai/kariana-umcp/issues)
- Review Unreal Engine Output Log
- Use the dashboard's Logs tab
- Refer to individual skill documentation

---

## Quick Reference

### Skill Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| name | Yes | Unique skill identifier |
| description | Yes | Brief description (<100 chars) |
| version | No | Semantic version (default: 1.0.0) |
| author | No | Skill creator |
| dependencies | No | Required packages/plugins |

### Socket Message Types

| Type | Description |
|------|-------------|
| discover_skills | List all available skills |
| load_skill | Load full skill instructions |
| find_skills | Search skills by query |
| execute_skill_script | Run skill script |

### Skills Directory

```
Plugins/KarianaUMCP/skills/
├── spawn-actor/SKILL.md
├── screenshot/SKILL.md
├── blueprint-helper/SKILL.md
└── level-organizer/SKILL.md
```

---

*Based on best practices from [Awesome Claude Skills](https://github.com/travisvn/awesome-claude-skills)*
