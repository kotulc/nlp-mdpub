"""Application-level configuration settings"""

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "mdpub"
    db_url: str = "sqlite:///mdpub.db"
    max_nesting: int = Field(default=6, ge=1, description="Max heading depth before flattening")
    max_versions: int = Field(default=10, ge=0, description="Max stored versions per doc; 0 disables")
    output_dir: str = Field(default="dist", description="Directory for exported MD/MDX + JSON files")
    output_format: str = Field(default="mdx", pattern="^(md|mdx)$", description="md or mdx")
    parser_config: str = Field(default="gfm-like", description="MarkdownIt parser preset name")
