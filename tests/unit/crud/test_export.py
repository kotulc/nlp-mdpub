"""Unit tests for core/export.py"""

from pathlib import Path
from uuid import uuid4

import yaml

from mdpub.core.export import build_body, build_mdx, write_doc
from mdpub.core.utils.hashing import sha256
from mdpub.crud.documents import commit_doc
from mdpub.crud.models import Document, Section, SectionBlock, SectionBlockEnum


# --- helpers ---

def _make_doc(**kwargs) -> Document:
    defaults = dict(
        slug="test-doc",
        markdown="# Hello\n\nWorld",
        hash=sha256("# Hello\n\nWorld"),
        path="docs/test-doc.md",
        frontmatter={"title": "Test Doc"},
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
    fm = yaml.safe_load(result.split("---\n", 2)[1])
    assert fm["slug"] == "test-doc"


def test_build_mdx_merges_user_frontmatter():
    """User-supplied frontmatter fields appear in the output header."""
    doc = _make_doc(frontmatter={"title": "My Page", "date": "2026-01-01"})
    result = build_mdx(doc, "# Body\n")
    fm = yaml.safe_load(result.split("---\n", 2)[1])
    assert fm["title"] == "My Page"
    assert fm["date"] == "2026-01-01"


def test_build_mdx_no_pipeline_fields():
    """doc_id and hash are NOT included in the frontmatter."""
    doc = _make_doc()
    result = build_mdx(doc, "# Body\n")
    fm = yaml.safe_load(result.split("---\n", 2)[1])
    assert "doc_id" not in fm
    assert "hash" not in fm


def test_build_mdx_body_follows_header():
    """The body string appears after the closing --- delimiter."""
    doc = _make_doc()
    result = build_mdx(doc, "# Hello\n\nWorld")
    _, _, body = result.partition("---\n\n")
    assert "# Hello" in body


def test_build_mdx_embeds_tags_and_metrics():
    """tags and metrics dicts are embedded in frontmatter when provided."""
    doc = _make_doc()
    result = build_mdx(doc, "body", tags={"nlp": 0.9}, metrics={"score": 1.0})
    fm = yaml.safe_load(result.split("---\n", 2)[1])
    assert fm["tags"] == {"nlp": 0.9}
    assert fm["metrics"] == {"score": 1.0}


def test_build_mdx_omits_empty_tags_metrics():
    """tags and metrics keys are omitted when None or empty."""
    doc = _make_doc()
    for tags_arg, metrics_arg in ((None, None), ({}, {})):
        result = build_mdx(doc, "body", tags=tags_arg, metrics=metrics_arg)
        fm = yaml.safe_load(result.split("---\n", 2)[1])
        assert "tags" not in fm
        assert "metrics" not in fm


# --- write_doc ---

def test_write_doc_creates_mdx(session, tmp_path):
    """write_doc produces a single .mdx file (no sidecar JSON)."""
    data = {
        "slug": "intro", "path": "docs/intro.md",
        "markdown": "# Hi", "hash": sha256("# Hi"), "frontmatter": {},
        "sections": [{"hash": sha256("# Hi"), "position": 0, "blocks": [
            {"content": "# Hi", "hash": sha256("# Hi"),
             "type": SectionBlockEnum.heading.value, "position": 0.0, "level": 1}
        ]}],
    }
    doc, _ = commit_doc(session, data)
    mdx_path = write_doc(doc, session, tmp_path)
    assert mdx_path.exists()
    assert not mdx_path.with_suffix(".json").exists()


def test_write_doc_mirrors_source_dir(session, tmp_path):
    """Output directory mirrors the source file's parent path."""
    data = {
        "slug": "guide", "path": "content/guides/guide.md",
        "markdown": "# Guide", "hash": sha256("# Guide"), "frontmatter": {},
        "sections": [],
    }
    doc, _ = commit_doc(session, data)
    mdx_path = write_doc(doc, session, tmp_path)
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
    mdx_path = write_doc(doc, session, tmp_path)
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
    mdx_path = write_doc(doc, session, tmp_path)
    fm = yaml.safe_load(mdx_path.read_text().split("---\n")[1])
    assert "doc_id" not in fm
    assert "hash" not in fm


def test_write_doc_frontmatter_has_tags_and_metrics(session, tmp_path):
    """Aggregated tags and metrics from DB sections appear in the .mdx frontmatter."""
    data = {
        "slug": "enriched", "path": "enriched.md",
        "markdown": "# E", "hash": sha256("# E"), "frontmatter": {},
        "sections": [{
            "hash": sha256("# E"), "position": 0,
            "tags": {"nlp": 0.9}, "metrics": {"score": 1.0},
            "blocks": [{"content": "# E", "hash": sha256("# E"),
                        "type": SectionBlockEnum.heading.value, "position": 0.0, "level": 1}],
        }],
    }
    doc, _ = commit_doc(session, data)
    mdx_path = write_doc(doc, session, tmp_path)
    fm = yaml.safe_load(mdx_path.read_text().split("---\n")[1])
    assert fm["tags"] == {"nlp": 0.9}
    assert fm["metrics"] == {"score": 1.0}
