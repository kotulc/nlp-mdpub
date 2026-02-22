"""Unit tests for core/export.py"""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import yaml
from sqlmodel import select

from mdpub.core.export import build_mdx, build_sidecar, write_doc
from mdpub.core.utils.hashing import sha256
from mdpub.crud.documents import commit_doc
from mdpub.crud.models import Document, DocumentVersion, Section, SectionBlock, SectionBlockEnum
from mdpub.crud.versioning import save_version


# --- helpers ---

def _make_doc(**kwargs) -> Document:
    defaults = dict(
        slug="test-doc",
        markdown="# Hello\n\nWorld",
        hash=sha256("# Hello\n\nWorld"),
        path="docs/test-doc.md",
        frontmatter={"title": "Test Doc"},
        committed_at=datetime(2026, 1, 1),
    )
    defaults.update(kwargs)
    return Document(**defaults)


def _make_section(doc_id, position=0) -> Section:
    return Section(document_id=doc_id, hash=sha256(f"sec{position}"), position=position)


def _make_block(section_id, content="Hello", position=0.0) -> SectionBlock:
    return SectionBlock(
        id=uuid4(),
        section_id=section_id,
        content=content,
        hash=sha256(content),
        type=SectionBlockEnum.paragraph,
        position=position,
    )


# --- build_mdx ---

def test_build_mdx_prepends_frontmatter():
    """Output starts with a YAML frontmatter block."""
    doc = _make_doc()
    result = build_mdx(doc)
    assert result.startswith("---\n")
    parts = result.split("---\n", 2)
    fm = yaml.safe_load(parts[1])
    assert fm["slug"] == "test-doc"
    assert fm["doc_id"] == str(doc.id)
    assert fm["hash"] == doc.hash


def test_build_mdx_merges_user_frontmatter():
    """User-supplied frontmatter fields appear in the output header."""
    doc = _make_doc(frontmatter={"title": "My Page", "date": "2026-01-01"})
    result = build_mdx(doc)
    parts = result.split("---\n", 2)
    fm = yaml.safe_load(parts[1])
    assert fm["title"] == "My Page"
    assert fm["date"] == "2026-01-01"


def test_build_mdx_body_follows_header():
    """The markdown body appears after the closing --- delimiter."""
    doc = _make_doc(markdown="# Hello\n\nWorld")
    result = build_mdx(doc)
    # After two --- delimiters the body starts
    _, _, body = result.partition("---\n\n")
    assert "# Hello" in body


def test_build_mdx_md_format():
    """fmt='md' works the same as 'mdx' for the frontmatter output."""
    doc = _make_doc()
    result = build_mdx(doc, fmt='md')
    assert result.startswith("---\n")


# --- build_sidecar ---

def test_build_sidecar_structure():
    """Sidecar dict has the expected top-level keys."""
    doc = _make_doc()
    result = build_sidecar(doc, [], {}, [])
    assert set(result.keys()) >= {"slug", "doc_id", "path", "hash", "committed_at", "frontmatter", "sections", "versions"}


def test_build_sidecar_sections_and_blocks():
    """Sections and their blocks are nested correctly."""
    doc = _make_doc()
    sec = _make_section(doc.id, position=0)
    blk = _make_block(sec.id, content="Para")
    result = build_sidecar(doc, [sec], {sec.id: [blk]}, [])
    assert len(result["sections"]) == 1
    assert result["sections"][0]["position"] == 0
    assert result["sections"][0]["blocks"][0]["content"] == "Para"


def test_build_sidecar_blocks_ordered_by_position():
    """Blocks within a section are sorted by position."""
    doc = _make_doc()
    sec = _make_section(doc.id)
    b1 = _make_block(sec.id, content="second", position=1.0)
    b0 = _make_block(sec.id, content="first", position=0.0)
    result = build_sidecar(doc, [sec], {sec.id: [b1, b0]}, [])
    contents = [b["content"] for b in result["sections"][0]["blocks"]]
    assert contents == ["first", "second"]


def test_build_sidecar_versions():
    """Version history entries are serialized with isoformat dates."""
    doc = _make_doc()
    version = DocumentVersion(
        document_id=doc.id,
        version_num=1,
        markdown="# old",
        hash=sha256("# old"),
        created_at=datetime(2026, 1, 1),
    )
    result = build_sidecar(doc, [], {}, [version])
    assert len(result["versions"]) == 1
    assert result["versions"][0]["version_num"] == 1
    assert result["versions"][0]["created_at"] == "2026-01-01T00:00:00"


def test_build_sidecar_committed_at_isoformat():
    """committed_at is serialized as an ISO 8601 string."""
    doc = _make_doc(committed_at=datetime(2026, 2, 22))
    result = build_sidecar(doc, [], {}, [])
    assert result["committed_at"] == "2026-02-22T00:00:00"


def test_build_sidecar_no_committed_at():
    """committed_at is None when not set on the document."""
    doc = _make_doc(committed_at=None)
    result = build_sidecar(doc, [], {}, [])
    assert result["committed_at"] is None


# --- write_doc ---

def test_write_doc_creates_files(session, tmp_path):
    """write_doc produces both an .mdx and a .json file."""
    from mdpub.crud.documents import commit_doc
    data = {
        "slug": "intro", "path": "docs/intro.md",
        "raw_markdown": "# Hi", "markdown": "# Hi",
        "hash": sha256("# Hi"), "frontmatter": {},
        "sections": [{"hash": sha256("# Hi"), "position": 0, "blocks": [
            {"content": "# Hi", "hash": sha256("# Hi"),
             "type": SectionBlockEnum.heading.value, "position": 0.0, "level": 1}
        ]}],
    }
    doc, _ = commit_doc(session, data)
    mdx_path, json_path = write_doc(doc, session, tmp_path)
    assert mdx_path.exists()
    assert json_path.exists()


def test_write_doc_mirrors_source_dir(session, tmp_path):
    """Output directory mirrors the source file's parent path."""
    data = {
        "slug": "guide", "path": "content/guides/guide.md",
        "raw_markdown": "# Guide", "markdown": "# Guide",
        "hash": sha256("# Guide"), "frontmatter": {},
        "sections": [],
    }
    doc, _ = commit_doc(session, data)
    mdx_path, _ = write_doc(doc, session, tmp_path)
    assert mdx_path == tmp_path / "content" / "guides" / "guide.mdx"


def test_write_doc_mdx_has_frontmatter(session, tmp_path):
    """The written .mdx file contains a YAML frontmatter block."""
    data = {
        "slug": "fm-test", "path": "fm-test.md",
        "raw_markdown": "# FM", "markdown": "# FM",
        "hash": sha256("# FM"), "frontmatter": {"title": "FM Test"},
        "sections": [],
    }
    doc, _ = commit_doc(session, data)
    mdx_path, _ = write_doc(doc, session, tmp_path)
    content = mdx_path.read_text()
    assert content.startswith("---\n")
    fm = yaml.safe_load(content.split("---\n")[1])
    assert fm["slug"] == "fm-test"
    assert fm["title"] == "FM Test"


def test_write_doc_json_has_sections(session, tmp_path):
    """The written .json sidecar contains a sections array."""
    data = {
        "slug": "json-test", "path": "json-test.md",
        "raw_markdown": "# J", "markdown": "# J",
        "hash": sha256("# J"), "frontmatter": {},
        "sections": [{"hash": sha256("# J"), "position": 0, "blocks": [
            {"content": "# J", "hash": sha256("# J"),
             "type": SectionBlockEnum.heading.value, "position": 0.0, "level": 1}
        ]}],
    }
    doc, _ = commit_doc(session, data)
    _, json_path = write_doc(doc, session, tmp_path)
    payload = json.loads(json_path.read_text())
    assert "sections" in payload
    assert len(payload["sections"]) == 1
