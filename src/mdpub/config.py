"""Config loading: reads config.yaml and merges overrides into a Settings instance"""

from pathlib import Path
from typing import Any

import yaml

from mdpub.settings import Settings


CONFIG_FILE = "config.yaml"


def load_config(config_path: str = None, overrides: dict[str, Any] = None) -> Settings:
    """Load Settings from config.yaml, then apply non-None overrides."""
    path = Path(config_path or CONFIG_FILE)
    data: dict[str, Any] = {}
    if path.exists():
        data = yaml.safe_load(path.read_text()) or {}
    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})
    return Settings(**data)
