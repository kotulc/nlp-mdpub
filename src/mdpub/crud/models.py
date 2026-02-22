"""Database table definitions for documents, sections, content blocks, etc."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, JSON, Text, String, UniqueConstraint
from sqlalchemy.orm import Mapped

from datetime import datetime
from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    """A markdown document and the originating content source of truth"""
    __tablename__ = "documents"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    slug: str = Field(..., index=True, nullable=False)
    markdown: str = Field(..., sa_column=Column(Text, nullable=False))
    hash: str = Field(..., sa_column=Column(String(64), nullable=False))
    frontmatter: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    path: str = Field(..., sa_column=Column(Text, nullable=False, unique=True))
    created_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    updated_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    sections: Mapped[List["Section"]] = Relationship(back_populates="document")
    meta: Mapped[List["DocumentMeta"]] = Relationship(back_populates="document")


class DocumentMeta(SQLModel, table=True):
    """Normalized key-value pairs for computed metadata about a document (e.g. word counts, metrics, etc.)"""
    __tablename__ = "document_meta"
    document_id: UUID = Field(foreign_key="documents.id", primary_key=True, nullable=False)
    key: str = Field(primary_key=True)
    value: str = Field(..., nullable=False)
    document: Mapped[Optional["Document"]] = Relationship(back_populates="meta")


class DocumentVersion(SQLModel, table=True):
    """Immutable snapshot of a Document at a prior state."""
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version_num", name="uq_docver_doc_num"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(..., foreign_key="documents.id", index=True, nullable=False)
    version_num: int = Field(..., nullable=False, description="Monotonically increasing per-document version number")
    markdown: str = Field(..., sa_column=Column(Text, nullable=False))
    hash: str = Field(..., sa_column=Column(String(64), nullable=False))
    frontmatter: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))


class SectionTag(SQLModel, table=True):
    """Many-to-many relationship between sections and tags"""
    __tablename__ = "section_tags"
    section_id: UUID = Field(foreign_key="sections.id", primary_key=True)
    tag_name: str = Field(foreign_key="tags.name", primary_key=True)
    relevance: float = Field(..., nullable=False)
    position: Optional[int] = Field(default=None, nullable=False)


class Section(SQLModel, table=True):
    """Logical grouping of content blocks within a document representing a top-level section"""
    __tablename__ = "sections"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True, nullable=False)
    hash: str = Field(..., sa_column=Column(String(64), nullable=False))
    position: int = Field(..., description="Position of the section within the document")
    hidden: bool = Field(default=False, nullable=False, description="Whether the section is hidden")
    updated_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    document: Mapped[Document] = Relationship(back_populates="sections")
    blocks: Mapped[List["SectionBlock"]] = Relationship(back_populates="section")
    metrics: Mapped[List["SectionMetric"]] = Relationship(back_populates="section")
    tags: Mapped[List["Tag"]] = Relationship(back_populates="sections", link_model=SectionTag)


class SectionBlockEnum(str, Enum):
    """Restrict the types of content blocks to a predefined set of elements"""
    content = "content"
    heading = "heading"
    paragraph = "paragraph"
    list = "list"
    table = "table"
    figure = "figure"
    footer = "footer"


class SectionBlock(SQLModel, table=True):
    """The fundamental unit of ordered content within a given section"""
    __tablename__ = "section_blocks"
    id: UUID = Field(..., primary_key=True)
    section_id: UUID = Field(..., foreign_key="sections.id")
    content: str = Field(..., sa_column=Column(Text, nullable=False))
    hash: str = Field(..., sa_column=Column(String(64), nullable=False))
    type: SectionBlockEnum = Field(..., nullable=False, description="Type of content block (e.g. heading, etc.)")
    position: float = Field(..., nullable=False, description="Position of the block within the section")
    updated_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    level: Optional[int] = Field(default=None, description="Nesting/indentation/heading level")
    section: Mapped[Optional["Section"]] = Relationship(back_populates="blocks")


class SectionMetric(SQLModel, table=True):
    """Section content based metrics (e.g. toxicity, sentiment, spam, etc.)"""
    __tablename__ = "section_metrics"
    section_id: UUID = Field(..., foreign_key="sections.id", primary_key=True)
    name: str = Field(..., primary_key=True)
    value: float = Field(..., nullable=False)
    recorded_at: datetime = Field(default_factory=datetime.now, sa_column=Column(DateTime(timezone=False), nullable=False))
    section: Mapped[Optional["Section"]] = Relationship(back_populates="metrics")


class Tag(SQLModel, table=True):
    """A tag or label that can be associated with sections for categorization, filtering, etc."""
    __tablename__ = "tags"
    name: str = Field(primary_key=True)
    category: str = Field(..., sa_column=Column(String(64), nullable=False))
    sections: Mapped[List[Section]] = Relationship(back_populates="tags", link_model=SectionTag)
