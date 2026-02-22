"""Unit tests for core/extract/extract.py"""

import pytest

from mdpub.core.extract.extract import extract_doc
from mdpub.core.parse import parse_file
from mdpub.core.models import ExtractedDoc


def test_extract_section_count(tmp_path):
    """extract_doc produces one section per qualifying heading."""
    f = tmp_path / "doc.md"
    f.write_text("# One\n\nPara.\n\n# Two\n\nPara.\n")
    doc = extract_doc(parse_file(f), max_nesting=1)
    assert isinstance(doc, ExtractedDoc)
    assert len(doc.sections) == 2


def test_extract_section_hash(tmp_path):
    """Each section has a non-empty hash."""
    f = tmp_path / "doc.md"
    f.write_text("# Section\n\nContent here.\n")
    doc = extract_doc(parse_file(f))
    assert all(len(s.hash) == 64 for s in doc.sections)


def test_extract_frontmatter_preserved(tmp_path):
    """extract_doc carries frontmatter through from ParsedDoc."""
    f = tmp_path / "doc.md"
    f.write_text("---\ntitle: My Title\n---\n# Body\n")
    doc = extract_doc(parse_file(f))
    assert doc.frontmatter == {"title": "My Title"}


def test_extract_slug_and_hash(tmp_path):
    """extract_doc slug and hash match the parsed source."""
    from mdpub.core.utils.hashing import sha256
    f = tmp_path / "my-doc.md"
    raw = "# Hello\n"
    f.write_text(raw)
    doc = extract_doc(parse_file(f))
    assert doc.slug == "my-doc"
    assert doc.hash == sha256(raw)


def test_extract_no_headings(tmp_path):
    """Document with no headings produces a single section."""
    f = tmp_path / "flat.md"
    f.write_text("Just a paragraph.\n\nAnother one.\n")
    doc = extract_doc(parse_file(f))
    assert len(doc.sections) == 1


def test_extract_max_nesting(tmp_path):
    """max_nesting=1 treats h2 as a block, not a section boundary."""
    f = tmp_path / "doc.md"
    f.write_text("# Top\n\n## Sub\n\nBody.\n")
    doc_nested = extract_doc(parse_file(f), max_nesting=2)
    doc_flat = extract_doc(parse_file(f), max_nesting=1)
    assert len(doc_nested.sections) == 2
    assert len(doc_flat.sections) == 1
