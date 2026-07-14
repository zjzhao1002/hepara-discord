import os
import logging
from typing import List
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def get_skills_path() -> Path:
    configured_path = os.getenv("SKILL_PATH")
    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path
    return PROJECT_ROOT / "skill"

def get_all_skill_names() -> List[str]:
    path = get_skills_path()
    if not path.exists():
        logger.info("Skill directory %s does not exist; skills agent is disabled.", path)
        return []
    if not path.is_dir():
        logger.warning("Skill path %s is not a directory; skills agent is disabled.", path)
        return []

    return sorted(x.name for x in path.iterdir() if x.is_dir())

def print_skills():
    skill_names = get_all_skill_names()
    if not skill_names:
        print("No available skills.")
        return

    print("Available external skills:")
    print("\n".join(skill_names))

if __name__ == "__main__":
    print_skills()