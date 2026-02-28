"""Application configuration: settings schema and config.yaml loader"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


CONFIG_FILE = "config.yaml"


class Settings(BaseModel):
    app_name:     str = "mdpub"
    db_url:       str = "sqlite:///mdpub.db"
    max_nesting:  int = Field(default=6,  ge=1, description="Max heading depth before flattening")
    max_versions: int = Field(default=10, ge=0, description="Max stored versions per doc; 0 disables")
    max_tags:     int = Field(default=0,  ge=0, description="Max tags per section in export; 0 = unlimited")
    max_metrics:  int = Field(default=0,  ge=0, description="Max metrics per section in export; 0 = unlimited")
    output_dir:   str = Field(default="dist",         description="Directory for exported MD/MDX + JSON files")
    output_format: str = Field(default="mdx", pattern="^(md|mdx)$", description="md or mdx")
    parser_config: str = Field(default="gfm-like",    description="MarkdownIt parser preset name")
    staging_dir:   str = Field(default=".mdpub/staging", description="Staging directory for extracted JSON")


def load_config(overrides: dict[str, Any] = None) -> Settings:
    """Load Settings from config.yaml, then MDPUB_<FIELD> env vars, then non-None CLI overrides."""
    data: dict[str, Any] = {}
    if Path(CONFIG_FILE).exists():
        try:
            data = yaml.safe_load(Path(CONFIG_FILE).read_text()) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid {CONFIG_FILE}: {e}") from e

    for name in Settings.model_fields:
        if val := os.getenv(f"MDPUB_{name.upper()}"):
            data[name] = val

    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})
    return Settings(**data)
