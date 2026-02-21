from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any

class Frontmatter(BaseModel):
    raw: dict[str, Any] = Field(default_factory=dict)

class Block(BaseModel):
    kind: str
    text: str
    meta: dict[str, Any] = Field(default_factory=dict)

class StructuredDocument(BaseModel):
    doc_id: str
    source_path: str
    slug: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    frontmatter: Frontmatter = Field(default_factory=Frontmatter)
    blocks: list[Block] = Field(default_factory=list)

    content_hash: str
    tags: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
