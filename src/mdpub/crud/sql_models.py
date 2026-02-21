from __future__ import annotations
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON, Text, DateTime
from sqlmodel import SQLModel, Field

class SQLModelBase(SQLModel):
    pass

class DocumentRow(SQLModelBase, table=True):
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)

    source_path: str = Field(index=True, sa_column=Column(Text, unique=True, nullable=False))
    doc_id: str = Field(index=True, sa_column=Column(Text, nullable=False))
    slug: str | None = Field(default=None, index=True, sa_column=Column(Text, nullable=True))
    content_hash: str = Field(index=True, sa_column=Column(Text, nullable=False))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

    frontmatter: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    blocks: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    metrics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
