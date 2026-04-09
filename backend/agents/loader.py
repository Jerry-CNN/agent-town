"""Agent config loader — reads and validates JSON agent files from disk."""
import json
from pathlib import Path

from backend.schemas import AgentConfig

# Canonical location of agent JSON config files.
# Each file must conform to the AgentConfig schema.
AGENTS_DIR = Path(__file__).parent.parent / "data" / "agents"


def load_all_agents() -> list[AgentConfig]:
    """Load all agent JSON configs from data/agents/, validate with Pydantic v2.

    Files are loaded in sorted order (alphabetical by filename) so the agent
    list is deterministic across restarts. Each file is validated through
    AgentConfig.model_validate() -- malformed configs raise ValidationError.

    Returns:
        List of validated AgentConfig objects, one per JSON file found.

    Raises:
        FileNotFoundError: If AGENTS_DIR does not exist.
        pydantic.ValidationError: If any agent JSON file fails schema validation.
    """
    if not AGENTS_DIR.exists():
        raise FileNotFoundError(
            f"Agent data directory not found: {AGENTS_DIR}. "
            "Expected JSON config files at backend/data/agents/*.json"
        )

    configs: list[AgentConfig] = []
    for f in sorted(AGENTS_DIR.glob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        configs.append(AgentConfig.model_validate(raw))
    return configs
