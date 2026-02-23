"""Application configuration: settings schema and config.yaml loader"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


CONFIG_FILE = "config.yaml"


class Settings(BaseModel):
    app_name: str = "mdpub"
    db_url: str = "sqlite:///mdpub.db"
    max_nesting: int = Field(default=6, ge=1, description="Max heading depth before flattening")
    max_versions: int = Field(default=10, ge=0, description="Max stored versions per doc; 0 disables")
    output_dir: str = Field(default="dist", description="Directory for exported MD/MDX + JSON files")
    output_format: str = Field(default="mdx", pattern="^(md|mdx)$", description="md or mdx")
    parser_config: str = Field(default="gfm-like", description="MarkdownIt parser preset name")
    staging_dir: str = Field(default=".mdpub/staging", description="Staging directory for extracted JSON")


def load_config(overrides: dict[str, Any] = None) -> Settings:
    """Load Settings: config.yaml, then MDPUB_DB_URL env var, then non-None CLI overrides."""
    data: dict[str, Any] = {}
    if Path(CONFIG_FILE).exists():
        data = yaml.safe_load(Path(CONFIG_FILE).read_text()) or {}
    if db_url := os.getenv("MDPUB_DB_URL"):
        data["db_url"] = db_url
    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})
    return Settings(**data)
