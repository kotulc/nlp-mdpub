"""Intermediate data models for the parse and extract pipeline"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from mdpub.crud.tables import SectionBlockEnum


@dataclass
class ExtractedBlock:
    content:  str
    hash:     str
    type:     SectionBlockEnum
    position: float
    level:    Optional[int] = None   # heading level (1-6) or None


@dataclass
class ExtractedSection:
    hash:     str
    position: int
    blocks:   list[ExtractedBlock] = field(default_factory=list)


@dataclass
class ParsedDoc:
    path:         Path
    slug:         str
    raw_markdown: str          # full file content (includes frontmatter)
    markdown:     str          # body only (frontmatter stripped)
    hash:         str          # sha256 of raw_markdown
    frontmatter:  dict[str, Any]
    tokens:       list         # markdown-it Token objects


@dataclass
class ExtractedDoc:
    slug:         str
    path:         str          # str for JSON serialization
    raw_markdown: str
    markdown:     str
    hash:         str
    frontmatter:  dict[str, Any]
    sections:     list[ExtractedSection] = field(default_factory=list)
