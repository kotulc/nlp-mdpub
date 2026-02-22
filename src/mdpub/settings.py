"""Application-level configuration settings"""

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "mdpub"
    db_url_env: str = "mdpub_DB_URL"
    max_versions: int = Field(
        default=10, ge=0,
        description="Max stored versions per document; 0 disables versioning"
    )
