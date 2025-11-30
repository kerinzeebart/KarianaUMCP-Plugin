"""
KarianaUMCP Skills Loader
========================
Progressive disclosure architecture for loading and managing skills.

Skills are specialized folders containing instructions, scripts, and resources
that can be dynamically discovered and loaded when relevant to tasks.

Based on best practices from: https://github.com/travisvn/awesome-claude-skills
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class SkillMetadata:
    """Lightweight skill metadata for discovery (~100 tokens)"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "unknown"
    dependencies: List[str] = field(default_factory=list)
    path: str = ""


@dataclass
class Skill:
    """Full skill with instructions and resources"""
    metadata: SkillMetadata
    instructions: str = ""
    scripts: Dict[str, str] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)


class SkillsLoader:
    """
    Loads and manages KarianaUMCP skills with progressive disclosure.

    Progressive disclosure architecture:
    1. Metadata loading (~100 tokens): Scan available skills
    2. Full instructions (<5k tokens): Load when skill applies
    3. Bundled resources: Load only as needed
    """

    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir:
            self.skills_dir = Path(skills_dir)
        else:
            # Default to plugin's skills directory
            self.skills_dir = Path(__file__).parent.parent.parent / "skills"

        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._full_cache: Dict[str, Skill] = {}

    def discover_skills(self) -> List[SkillMetadata]:
        """
        Phase 1: Discover available skills (metadata only).
        Returns lightweight metadata for all skills (~100 tokens each).
        """
        skills = []

        if not self.skills_dir.exists():
            return skills

        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                metadata = self._load_metadata(skill_path)
                if metadata:
                    skills.append(metadata)
                    self._metadata_cache[metadata.name] = metadata

        return skills

    def _load_metadata(self, skill_path: Path) -> Optional[SkillMetadata]:
        """Load skill metadata from SKILL.md frontmatter"""
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            return None

        try:
            content = skill_md.read_text(encoding='utf-8')
            frontmatter = self._parse_frontmatter(content)

            if not frontmatter:
                return None

            return SkillMetadata(
                name=frontmatter.get('name', skill_path.name),
                description=frontmatter.get('description', ''),
                version=frontmatter.get('version', '1.0.0'),
                author=frontmatter.get('author', 'unknown'),
                dependencies=frontmatter.get('dependencies', []),
                path=str(skill_path)
            )
        except Exception as e:
            print(f"Error loading skill metadata from {skill_path}: {e}")
            return None

    def _parse_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse YAML frontmatter from SKILL.md"""
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

        if not match:
            return None

        frontmatter_text = match.group(1)
        result = {}

        # Simple YAML parsing (no external dependencies)
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Handle lists
                if value.startswith('[') and value.endswith(']'):
                    items = value[1:-1].split(',')
                    result[key] = [item.strip().strip('"\'') for item in items if item.strip()]
                elif value.startswith('-'):
                    # Multi-line list, collect items
                    if key not in result:
                        result[key] = []
                elif value:
                    result[key] = value.strip('"\'')
            elif line.startswith('-') and result:
                # List item continuation
                last_key = list(result.keys())[-1]
                if isinstance(result[last_key], list):
                    result[last_key].append(line[1:].strip().strip('"\''))

        return result if result else None

    def load_skill(self, skill_name: str) -> Optional[Skill]:
        """
        Phase 2: Load full skill instructions (<5k tokens).
        Call when skill is determined to be relevant to task.
        """
        if skill_name in self._full_cache:
            return self._full_cache[skill_name]

        # Find skill path
        skill_path = None
        if skill_name in self._metadata_cache:
            skill_path = Path(self._metadata_cache[skill_name].path)
        else:
            potential_path = self.skills_dir / skill_name
            if potential_path.exists():
                skill_path = potential_path

        if not skill_path:
            return None

        metadata = self._metadata_cache.get(skill_name) or self._load_metadata(skill_path)
        if not metadata:
            return None

        # Load full instructions
        skill_md = skill_path / "SKILL.md"
        content = skill_md.read_text(encoding='utf-8')

        # Remove frontmatter
        instructions = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

        skill = Skill(
            metadata=metadata,
            instructions=instructions.strip()
        )

        self._full_cache[skill_name] = skill
        return skill

    def load_skill_scripts(self, skill_name: str) -> Dict[str, str]:
        """
        Phase 3: Load skill scripts (only when needed).
        Returns dict of script_name -> script_content.
        """
        skill = self.load_skill(skill_name)
        if not skill:
            return {}

        scripts_dir = Path(skill.metadata.path) / "scripts"
        if not scripts_dir.exists():
            return {}

        scripts = {}
        for script_file in scripts_dir.iterdir():
            if script_file.is_file():
                try:
                    scripts[script_file.name] = script_file.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"Error loading script {script_file}: {e}")

        skill.scripts = scripts
        return scripts

    def find_relevant_skills(self, query: str) -> List[SkillMetadata]:
        """
        Find skills relevant to a given query/task description.
        Uses simple keyword matching on skill names and descriptions.
        """
        if not self._metadata_cache:
            self.discover_skills()

        query_lower = query.lower()
        query_words = set(query_lower.split())

        relevant = []
        for metadata in self._metadata_cache.values():
            # Check name match
            if metadata.name.lower() in query_lower:
                relevant.append((metadata, 10))  # High priority
                continue

            # Check description match
            desc_words = set(metadata.description.lower().split())
            overlap = len(query_words & desc_words)
            if overlap > 0:
                relevant.append((metadata, overlap))

        # Sort by relevance score
        relevant.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in relevant]

    def get_skill_summary(self) -> Dict[str, Any]:
        """Get summary of all available skills for discovery"""
        if not self._metadata_cache:
            self.discover_skills()

        return {
            "total_skills": len(self._metadata_cache),
            "skills": [
                {
                    "name": m.name,
                    "description": m.description,
                    "version": m.version
                }
                for m in self._metadata_cache.values()
            ]
        }


# Global loader instance
_skills_loader: Optional[SkillsLoader] = None


def get_skills_loader() -> SkillsLoader:
    """Get or create global skills loader"""
    global _skills_loader
    if _skills_loader is None:
        _skills_loader = SkillsLoader()
    return _skills_loader


def discover_skills() -> List[Dict[str, Any]]:
    """Discover all available skills (for socket server handler)"""
    loader = get_skills_loader()
    skills = loader.discover_skills()
    return [
        {
            "name": s.name,
            "description": s.description,
            "version": s.version,
            "author": s.author,
            "dependencies": s.dependencies
        }
        for s in skills
    ]


def load_skill(skill_name: str) -> Optional[Dict[str, Any]]:
    """Load full skill instructions (for socket server handler)"""
    loader = get_skills_loader()
    skill = loader.load_skill(skill_name)

    if not skill:
        return None

    return {
        "name": skill.metadata.name,
        "description": skill.metadata.description,
        "version": skill.metadata.version,
        "instructions": skill.instructions,
        "has_scripts": bool(skill.scripts)
    }


def find_skills(query: str) -> List[Dict[str, Any]]:
    """Find relevant skills for a query (for socket server handler)"""
    loader = get_skills_loader()
    skills = loader.find_relevant_skills(query)
    return [
        {
            "name": s.name,
            "description": s.description
        }
        for s in skills
    ]


# Export
__all__ = [
    'SkillMetadata',
    'Skill',
    'SkillsLoader',
    'get_skills_loader',
    'discover_skills',
    'load_skill',
    'find_skills'
]
