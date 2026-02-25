"""Unit tests for core/extract/extract.py"""

from mdpub.core.extract.extract import extract_doc
from mdpub.core.parse import parse_file
from mdpub.core.models import StagedDoc
from mdpub.crud.models import SectionBlockEnum


def test_extract_returns_staged_doc(tmp_path):
    """extract_doc returns a StagedDoc instance."""
    f = tmp_path / "doc.md"
    f.write_text("# One\n\nPara.\n")
    assert isinstance(extract_doc(parse_file(f)), StagedDoc)


def test_extract_flat_blocks(tmp_path):
    """extract_doc produces a flat block list; headings do not create section boundaries."""
    f = tmp_path / "doc.md"
    f.write_text("# One\n\nPara.\n\n# Two\n\nPara.\n")
    doc = extract_doc(parse_file(f))
    # heading + para + heading + para = 4 blocks (no nesting)
    assert len(doc.content) == 4


def test_extract_frontmatter_preserved(tmp_path):
    """extract_doc carries frontmatter through from ParsedDoc."""
    f = tmp_path / "doc.md"
    f.write_text("---\ntitle: My Title\n---\n# Body\n")
    doc = extract_doc(parse_file(f))
    assert doc.frontmatter == {"title": "My Title"}


def test_extract_slug_from_filename(tmp_path):
    """extract_doc slug matches the parsed source slug."""
    f = tmp_path / "my-doc.md"
    f.write_text("# Hello\n")
    assert extract_doc(parse_file(f)).slug == "my-doc"


def test_extract_block_types(tmp_path):
    """extract_doc correctly classifies block types in the flat list."""
    f = tmp_path / "doc.md"
    f.write_text("# Title\n\nA paragraph.\n")
    doc = extract_doc(parse_file(f))
    types = [b.type for b in doc.content]
    assert SectionBlockEnum.heading in types
    assert SectionBlockEnum.paragraph in types


def test_extract_no_headings(tmp_path):
    """Document with no headings produces a flat list of paragraph blocks."""
    f = tmp_path / "flat.md"
    f.write_text("Just a paragraph.\n\nAnother one.\n")
    doc = extract_doc(parse_file(f))
    assert len(doc.content) == 2
    assert all(b.type == SectionBlockEnum.paragraph for b in doc.content)
