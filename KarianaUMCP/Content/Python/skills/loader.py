"""
KarianaUMCP Skills Loader
=========================
Load skill manifests from JSON files.
"""

import os
import json
from typing import Dict, Any, List, Optional


class SkillLoader:
    """Loads and manages skill manifests"""

    def __init__(self, manifests_dir: Optional[str] = None):
        if manifests_dir is None:
            # Default to manifests directory relative to this file
            self.manifests_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "manifests"
            )
        else:
            self.manifests_dir = manifests_dir

        self.skills: Dict[str, Dict] = {}
        self.load_all()

    def load_all(self):
        """Load all skill manifests from the manifests directory"""
        if not os.path.exists(self.manifests_dir):
            os.makedirs(self.manifests_dir, exist_ok=True)
            return

        for filename in os.listdir(self.manifests_dir):
            if filename.endswith(".skill.json") or filename.endswith(".json"):
                self.load_skill(os.path.join(self.manifests_dir, filename))

    def load_skill(self, filepath: str) -> Optional[Dict]:
        """Load a single skill manifest"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                skill = json.load(f)

            # Validate required fields
            if not skill.get("name"):
                print(f"SkillLoader: Skipping {filepath} - missing 'name' field")
                return None

            # Add to skills registry
            self.skills[skill["name"]] = skill
            return skill

        except json.JSONDecodeError as e:
            print(f"SkillLoader: Invalid JSON in {filepath}: {e}")
            return None
        except Exception as e:
            print(f"SkillLoader: Failed to load {filepath}: {e}")
            return None

    def get_skill(self, name: str) -> Optional[Dict]:
        """Get a skill by name"""
        return self.skills.get(name)

    def list_skills(self) -> List[Dict]:
        """List all available skills"""
        return [
            {
                "name": name,
                "description": skill.get("description", ""),
                "steps": len(skill.get("steps", [])),
                "parameters": list(skill.get("parameters", {}).keys())
            }
            for name, skill in self.skills.items()
        ]

    def create_skill(self, skill_data: Dict) -> bool:
        """Create a new skill manifest"""
        name = skill_data.get("name")
        if not name:
            return False

        # Save to file
        filename = f"{name}.skill.json"
        filepath = os.path.join(self.manifests_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(skill_data, f, indent=2)

            # Add to registry
            self.skills[name] = skill_data
            return True

        except Exception as e:
            print(f"SkillLoader: Failed to save skill {name}: {e}")
            return False


# Global loader instance
_loader: Optional[SkillLoader] = None


def get_loader() -> SkillLoader:
    """Get the global skill loader"""
    global _loader
    if _loader is None:
        _loader = SkillLoader()
    return _loader


def load_skill(name: str) -> Optional[Dict]:
    """Load a skill by name"""
    return get_loader().get_skill(name)


def list_skills() -> List[Dict]:
    """List all skills"""
    return get_loader().list_skills()
