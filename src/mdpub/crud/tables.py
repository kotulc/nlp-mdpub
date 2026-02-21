from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, Text, String
from sqlalchemy.orm import Mapped

from datetime import datetime
from sqlmodel import Field, SQLModel


class DocumentMeta(SQLModel, table=True):
    __tablename__ = "document_meta"
    document_id: UUID = Field(foreign_key="documents.id", index=True, nullable=False)
    key: str = Field(primary_key=True)
    value: str = Field(..., nullable=False)
    document: Mapped[Optional["Document"]] = Relationship(back_populates="meta")


class Document(SQLModel, table=True):
    __tablename__ = "documents"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    slug: str = Field(..., index=True, unique=True, nullable=False)
    markdown: str = Field(..., sa_column=Column(Text, nullable=False))
    hash: str = Field(..., sa_column=Column(String(64), nullable=False))
    frontmatter: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    updated_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    sections: Mapped[List["Section"]] = Relationship(back_populates="document")
    meta: Mapped[List[DocumentMeta]] = Relationship(back_populates="document")


class SectionBlockEnum(str, Enum):
    content = "content"
    heading = "heading"
    paragraph = "paragraph"
    list = "list"
    table = "table"
    figure = "figure"
    footer = "footer"


class SectionBlock(SQLModel, table=True):
    __tablename__ = "section_blocks"
    id: UUID = Field(..., primary_key=True)
    section_id: UUID = Field(..., foreign_key="sections.id", primary_key=True)
    content: str = Field(..., sa_column=Column(Text, nullable=False))
    hash: str = Field(..., sa_column=Column(String(64), nullable=False))
    type: str = Field(..., nullable=False, description="Type of content block (e.g. heading, etc.)")
    position: float = Field(..., nullable=False, description="Position of the block within the section")
    updated_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    level: Optional[int] = Field(default=None, description="Nesting/indentation/heading level")
    section: Mapped[Optional["Section"]] = Relationship(back_populates="blocks")


class SectionMetric(SQLModel, table=True):
    __tablename__ = "section_metrics"
    section_id: UUID = Field(..., foreign_key="sections.id", primary_key=True)
    name: str = Field(..., primary_key=True)
    value: float = Field(..., nullable=False)
    recorded_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    section: Mapped[Optional["Section"]] = Relationship(back_populates="metrics")


class SectionTag(SQLModel, table=True):
    __tablename__ = "section_tags"
    section_id: UUID = Field(foreign_key="sections.id", primary_key=True)
    tag_name: str = Field(foreign_key="tags.name", primary_key=True)
    relevance: float = Field(..., nullable=False)
    position: Optional[int] = Field(default=None, nullable=False)


class Section(SQLModel, table=True):
    __tablename__ = "sections"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True, nullable=False)
    position: int = Field(..., description="Position of the section within the document")
    hidden: bool = Field(default=False, nullable=False, description="Whether the section is hidden")
    document: Mapped[Document] = Relationship(back_populates="sections")
    blocks: Mapped[List[SectionBlock]] = Relationship(back_populates="section")
    metrics: Mapped[List[SectionMetric]] = Relationship(back_populates="section")
    tags: Mapped[List["Tag"]] = Relationship(back_populates="sections", link_model=SectionTag)


class Tag(SQLModel, table=True):
    __tablename__ = "tags"
    name: str = Field(primary_key=True)
    category: str = Field(..., sa_column=Column(String(64), nullable=False))
    sections: Mapped[List[Section]] = Relationship(back_populates="tags", link_model=SectionTag)
