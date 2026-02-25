"""Intermediate data models for the parse and extract pipeline"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from mdpub.crud.models import SectionBlockEnum


class StagedBlock(BaseModel):
    """A single typed content block from a markdown document."""
    type: SectionBlockEnum
    content: str
    level: Optional[int] = None     # heading level (1-6); None for non-headings


class StagedDoc(BaseModel):
    """Public staging contract: source-faithful content written by extract, read by commit."""
    slug: str
    path: str
    markdown: str                   # body without frontmatter (for versioning + doc hash)
    frontmatter: dict[str, Any] = {}
    blocks: list[StagedBlock]       # flat ordered list; no sections, hashes, or positions


@dataclass
class ParsedDoc:
    """Internal parse result carrying markdown-it tokens; not persisted."""
    path:         Path
    slug:         str
    raw_markdown: str          # full file content (includes frontmatter)
    markdown:     str          # body only (frontmatter stripped)
    frontmatter:  dict[str, Any]
    tokens:       list         # markdown-it Token objects
