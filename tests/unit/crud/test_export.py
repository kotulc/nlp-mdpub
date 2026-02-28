"""Unit tests for core/export.py"""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import yaml
from sqlmodel import select

from mdpub.core.export import build_body, build_mdx, build_sidecar, write_doc
from mdpub.core.utils.hashing import sha256
from mdpub.crud.documents import commit_doc
from mdpub.crud.models import (
    Document, Section, SectionBlock, SectionBlockEnum, SectionMetric, SectionTag, Tag,
)


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


def _make_section(doc_id, position=0, hidden=False) -> Section:
    return Section(document_id=doc_id, hash=sha256(f"sec{position}"), position=position, hidden=hidden)


def _make_block(section_id, content="Hello", position=0.0) -> SectionBlock:
    return SectionBlock(
        id=uuid4(),
        section_id=section_id,
        content=content,
        hash=sha256(content),
        type=SectionBlockEnum.paragraph,
        position=position,
    )


def _make_tag(section_id, tag_name, position=0) -> SectionTag:
    return SectionTag(section_id=section_id, tag_name=tag_name, relevance=1.0, position=position)


def _make_metric(section_id, name, value) -> SectionMetric:
    return SectionMetric(section_id=section_id, name=name, value=value)


# --- build_body ---

def test_build_body_joins_blocks():
    """Blocks within a section are joined with double newlines."""
    doc = _make_doc()
    sec = _make_section(doc.id)
    b0 = _make_block(sec.id, content="Para one.", position=0.0)
    b1 = _make_block(sec.id, content="Para two.", position=1.0)
    result = build_body([sec], {sec.id: [b0, b1]})
    assert "Para one." in result
    assert "Para two." in result
    assert result == "Para one.\n\nPara two."


def test_build_body_skips_hidden():
    """Hidden sections are excluded from the body output."""
    doc = _make_doc()
    visible = _make_section(doc.id, position=0, hidden=False)
    hidden = _make_section(doc.id, position=1, hidden=True)
    b_vis = _make_block(visible.id, content="Visible")
    b_hid = _make_block(hidden.id, content="Hidden")
    result = build_body([visible, hidden], {visible.id: [b_vis], hidden.id: [b_hid]})
    assert "Visible" in result
    assert "Hidden" not in result


def test_build_body_respects_section_order():
    """Sections are ordered by position, not insertion order."""
    doc = _make_doc()
    s0 = _make_section(doc.id, position=0)
    s1 = _make_section(doc.id, position=1)
    b0 = _make_block(s0.id, content="First")
    b1 = _make_block(s1.id, content="Second")
    result = build_body([s1, s0], {s0.id: [b0], s1.id: [b1]})
    assert result.index("First") < result.index("Second")


def test_build_body_respects_block_order():
    """Blocks within a section are sorted by position."""
    doc = _make_doc()
    sec = _make_section(doc.id)
    late = _make_block(sec.id, content="late", position=1.0)
    early = _make_block(sec.id, content="early", position=0.0)
    result = build_body([sec], {sec.id: [late, early]})
    assert result.index("early") < result.index("late")


def test_build_body_empty():
    """No sections produces an empty string."""
    assert build_body([], {}) == ""


# --- build_mdx ---

def test_build_mdx_prepends_frontmatter():
    """Output starts with a YAML frontmatter block containing slug."""
    doc = _make_doc()
    result = build_mdx(doc, "# Hello\n")
    assert result.startswith("---\n")
    parts = result.split("---\n", 2)
    fm = yaml.safe_load(parts[1])
    assert fm["slug"] == "test-doc"


def test_build_mdx_merges_user_frontmatter():
    """User-supplied frontmatter fields appear in the output header."""
    doc = _make_doc(frontmatter={"title": "My Page", "date": "2026-01-01"})
    result = build_mdx(doc, "# Body\n")
    parts = result.split("---\n", 2)
    fm = yaml.safe_load(parts[1])
    assert fm["title"] == "My Page"
    assert fm["date"] == "2026-01-01"


def test_build_mdx_no_pipeline_fields():
    """doc_id and hash are NOT included in the frontmatter."""
    doc = _make_doc()
    result = build_mdx(doc, "# Body\n")
    parts = result.split("---\n", 2)
    fm = yaml.safe_load(parts[1])
    assert "doc_id" not in fm
    assert "hash" not in fm


def test_build_mdx_body_follows_header():
    """The body string appears after the closing --- delimiter."""
    doc = _make_doc()
    result = build_mdx(doc, "# Hello\n\nWorld")
    _, _, body = result.partition("---\n\n")
    assert "# Hello" in body


# --- build_sidecar ---

def test_build_sidecar_structure():
    """Sidecar dict has the expected minimal top-level keys."""
    doc = _make_doc()
    result = build_sidecar(doc, [], {}, {})
    assert set(result.keys()) == {"slug", "path", "committed_at", "frontmatter", "sections"}


def test_build_sidecar_no_internal_fields():
    """doc_id, hash, and versions are not present in the sidecar."""
    doc = _make_doc()
    result = build_sidecar(doc, [], {}, {})
    assert "doc_id" not in result
    assert "hash" not in result
    assert "versions" not in result


def test_build_sidecar_section_tags_and_metrics():
    """Sections include tags and metrics from the provided dicts."""
    doc = _make_doc()
    sec = _make_section(doc.id, position=0)
    tag = _make_tag(sec.id, "nlp", position=0)
    metric = _make_metric(sec.id, "sentiment", 0.8)
    result = build_sidecar(doc, [sec], {sec.id: [tag]}, {sec.id: [metric]})
    assert len(result["sections"]) == 1
    s = result["sections"][0]
    assert s["tags"] == {"nlp": 1.0}
    assert s["metrics"] == {"sentiment": 0.8}


def test_build_sidecar_tag_order():
    """Tags within a section are sorted by SectionTag.position."""
    doc = _make_doc()
    sec = _make_section(doc.id)
    t0 = _make_tag(sec.id, "first", position=0)
    t1 = _make_tag(sec.id, "second", position=1)
    result = build_sidecar(doc, [sec], {sec.id: [t1, t0]}, {})
    assert list(result["sections"][0]["tags"].keys()) == ["first", "second"]


def test_build_sidecar_excludes_hidden():
    """Hidden sections are omitted from the sections list."""
    doc = _make_doc()
    visible = _make_section(doc.id, position=0, hidden=False)
    hidden = _make_section(doc.id, position=1, hidden=True)
    result = build_sidecar(doc, [visible, hidden], {}, {})
    assert len(result["sections"]) == 1
    assert result["sections"][0]["position"] == 0


def test_build_sidecar_max_tags_truncates():
    """max_tags=1 limits the tags dict to the first 1 entry (by position)."""
    doc = _make_doc()
    sec = _make_section(doc.id)
    tags = [_make_tag(sec.id, name, position=i) for i, name in enumerate(["a", "b", "c"])]
    result = build_sidecar(doc, [sec], {sec.id: tags}, {}, max_tags=1)
    assert list(result["sections"][0]["tags"].keys()) == ["a"]


def test_build_sidecar_max_metrics_truncates():
    """max_metrics=1 limits the metrics dict to 1 entry."""
    doc = _make_doc()
    sec = _make_section(doc.id)
    metrics = [_make_metric(sec.id, name, float(i)) for i, name in enumerate(["x", "y", "z"])]
    result = build_sidecar(doc, [sec], {}, {sec.id: metrics}, max_metrics=1)
    assert len(result["sections"][0]["metrics"]) == 1


def test_build_sidecar_zero_means_unlimited():
    """max_tags=0 returns all tags as a dict (0 is the unlimited sentinel)."""
    doc = _make_doc()
    sec = _make_section(doc.id)
    tags = [_make_tag(sec.id, name, position=i) for i, name in enumerate(["a", "b", "c"])]
    result = build_sidecar(doc, [sec], {sec.id: tags}, {}, max_tags=0)
    assert list(result["sections"][0]["tags"].keys()) == ["a", "b", "c"]


def test_build_sidecar_committed_at_isoformat():
    """committed_at is serialized as an ISO 8601 string."""
    doc = _make_doc(committed_at=datetime(2026, 2, 22))
    result = build_sidecar(doc, [], {}, {})
    assert result["committed_at"] == "2026-02-22T00:00:00"


def test_build_sidecar_no_committed_at():
    """committed_at is None when not set on the document."""
    doc = _make_doc(committed_at=None)
    result = build_sidecar(doc, [], {}, {})
    assert result["committed_at"] is None


# --- write_doc ---

def test_write_doc_creates_files(session, tmp_path):
    """write_doc produces both an .mdx and a .json file."""
    data = {
        "slug": "intro", "path": "docs/intro.md",
        "markdown": "# Hi", "hash": sha256("# Hi"), "frontmatter": {},
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
        "markdown": "# Guide", "hash": sha256("# Guide"), "frontmatter": {},
        "sections": [],
    }
    doc, _ = commit_doc(session, data)
    mdx_path, _ = write_doc(doc, session, tmp_path)
    assert mdx_path == tmp_path / "content" / "guides" / "guide.mdx"


def test_write_doc_mdx_has_frontmatter(session, tmp_path):
    """The written .mdx file contains a YAML frontmatter block with slug and user fields."""
    data = {
        "slug": "fm-test", "path": "fm-test.md",
        "markdown": "# FM", "hash": sha256("# FM"),
        "frontmatter": {"title": "FM Test"},
        "sections": [],
    }
    doc, _ = commit_doc(session, data)
    mdx_path, _ = write_doc(doc, session, tmp_path)
    content = mdx_path.read_text()
    assert content.startswith("---\n")
    fm = yaml.safe_load(content.split("---\n")[1])
    assert fm["slug"] == "fm-test"
    assert fm["title"] == "FM Test"


def test_write_doc_mdx_no_pipeline_fields(session, tmp_path):
    """The written .mdx frontmatter does not include doc_id or hash."""
    data = {
        "slug": "clean", "path": "clean.md",
        "markdown": "# Clean", "hash": sha256("# Clean"), "frontmatter": {},
        "sections": [],
    }
    doc, _ = commit_doc(session, data)
    mdx_path, _ = write_doc(doc, session, tmp_path)
    fm = yaml.safe_load(mdx_path.read_text().split("---\n")[1])
    assert "doc_id" not in fm
    assert "hash" not in fm


def test_write_doc_json_has_sections(session, tmp_path):
    """The written .json sidecar contains a sections array with tags and metrics keys."""
    data = {
        "slug": "json-test", "path": "json-test.md",
        "markdown": "# J", "hash": sha256("# J"), "frontmatter": {},
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
    sec = payload["sections"][0]
    assert "tags" in sec
    assert "metrics" in sec
    assert "blocks" not in sec
