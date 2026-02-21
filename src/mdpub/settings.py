from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = "mdpub"
    db_url_env: str = "mdpub_DB_URL"
