"""Unit tests for crud/documents.py"""

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from mdpub.core.utils.hashing import sha256
from mdpub.crud.documents import commit_doc, get_by_path, get_by_slug, _replace_sections
from mdpub.crud.models import Document, DocumentVersion, Section, SectionBlock, SectionBlockEnum


# --- helpers ---

def _make_staged(
    slug: str = "test-doc",
    markdown: str = "# Hello\n\nWorld",
    path: str = "docs/test-doc.md",
    frontmatter: dict = None,
    sections: list = None,
    ) -> dict:
    """Build a minimal staged ExtractedDoc dict."""
    raw = markdown
    if sections is None:
        sections = [
            {
                "hash": sha256("# Hello"),
                "position": 0,
                "blocks": [
                    {
                        "content": "# Hello",
                        "hash": sha256("# Hello"),
                        "type": SectionBlockEnum.heading.value,
                        "position": 0.0,
                        "level": 1,
                    }
                ],
            }
        ]
    return {
        "slug": slug,
        "path": path,
        "raw_markdown": raw,
        "markdown": markdown,
        "hash": sha256(raw),
        "frontmatter": frontmatter or {},
        "sections": sections,
    }


# --- get_by_path ---

def test_get_by_path_found(session, doc):
    """Returns the Document when the path exists."""
    result = get_by_path(session, doc.path)
    assert result is not None
    assert result.id == doc.id


def test_get_by_path_missing(session):
    """Returns None when the path is not in the database."""
    result = get_by_path(session, "no/such/path.md")
    assert result is None


# --- get_by_slug ---

def test_get_by_slug_found(session, doc):
    """Returns the Document when the slug exists."""
    result = get_by_slug(session, doc.slug)
    assert result is not None
    assert result.id == doc.id


def test_get_by_slug_missing(session):
    """Returns None when the slug is not in the database."""
    result = get_by_slug(session, "no-such-slug")
    assert result is None


# --- commit_doc: create ---

def test_commit_doc_creates_new(session):
    """A new path results in a Document being inserted with status 'created'."""
    data = _make_staged(slug="brand-new", path="docs/brand-new.md")
    doc, status = commit_doc(session, data)
    assert status == "created"
    assert get_by_path(session, "docs/brand-new.md") is not None


def test_commit_doc_creates_sections(session):
    """Sections and blocks are inserted for a new document."""
    data = _make_staged(slug="with-sections", path="docs/with-sections.md")
    doc, _ = commit_doc(session, data)
    sections = session.exec(select(Section).where(Section.document_id == doc.id)).all()
    assert len(sections) == 1
    blocks = session.exec(select(SectionBlock).where(SectionBlock.section_id == sections[0].id)).all()
    assert len(blocks) == 1


def test_commit_doc_stores_path(session):
    """The source file path is persisted on the Document."""
    data = _make_staged(slug="path-test", path="some/file.md")
    doc, _ = commit_doc(session, data)
    assert doc.path == "some/file.md"


# --- commit_doc: unchanged ---

def test_commit_doc_unchanged(session):
    """Same hash on re-commit returns 'unchanged' and makes no DB changes."""
    data = _make_staged(slug="stable", path="docs/stable.md")
    doc, _ = commit_doc(session, data)
    original_updated_at = doc.updated_at

    _, status = commit_doc(session, data)
    assert status == "unchanged"
    refreshed = get_by_path(session, "docs/stable.md")
    assert refreshed.updated_at == original_updated_at


def test_commit_doc_unchanged_no_version(session):
    """No DocumentVersion is created when content is unchanged."""
    data = _make_staged(slug="stable-v", path="docs/stable-v.md")
    doc, _ = commit_doc(session, data)
    commit_doc(session, data)
    versions = session.exec(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
    ).all()
    assert len(versions) == 0


# --- commit_doc: update ---

def test_commit_doc_updated(session):
    """Different hash triggers a version snapshot and returns 'updated'."""
    data = _make_staged(slug="evolving", path="docs/evolving.md", markdown="# v1")
    doc, _ = commit_doc(session, data)

    data2 = _make_staged(slug="evolving", path="docs/evolving.md", markdown="# v2")
    _, status = commit_doc(session, data2)
    assert status == "updated"

    versions = session.exec(
        select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
    ).all()
    assert len(versions) == 1
    assert versions[0].markdown == "# v1"


def test_commit_doc_replaces_sections(session):
    """Sections and blocks are replaced (not duplicated) on update."""
    data = _make_staged(slug="replace-me", path="docs/replace-me.md", sections=[
        {"hash": sha256("old"), "position": 0, "blocks": [
            {"content": "old", "hash": sha256("old"),
             "type": SectionBlockEnum.paragraph.value, "position": 0.0, "level": None}
        ]}
    ])
    doc, _ = commit_doc(session, data)

    new_sections = [
        {"hash": sha256("new1"), "position": 0, "blocks": [
            {"content": "new1", "hash": sha256("new1"),
             "type": SectionBlockEnum.paragraph.value, "position": 0.0, "level": None}
        ]},
        {"hash": sha256("new2"), "position": 1, "blocks": [
            {"content": "new2", "hash": sha256("new2"),
             "type": SectionBlockEnum.paragraph.value, "position": 0.0, "level": None}
        ]},
    ]
    data2 = _make_staged(slug="replace-me", path="docs/replace-me.md", markdown="# updated", sections=new_sections)
    commit_doc(session, data2)

    sections = session.exec(select(Section).where(Section.document_id == doc.id)).all()
    assert len(sections) == 2
    all_blocks = []
    for s in sections:
        all_blocks += session.exec(
            select(SectionBlock).where(SectionBlock.section_id == s.id)
        ).all()
    assert len(all_blocks) == 2
    contents = {b.content for b in all_blocks}
    assert contents == {"new1", "new2"}


# --- identity: path is primary key, not slug ---

def test_same_slug_different_paths_are_separate_documents(session):
    """Two files with the same slug but different paths are stored as distinct documents."""
    data_a = _make_staged(slug="intro", path="docs/intro.md", markdown="# Docs Intro")
    data_b = _make_staged(slug="intro", path="posts/intro.md", markdown="# Posts Intro")

    doc_a, status_a = commit_doc(session, data_a)
    doc_b, status_b = commit_doc(session, data_b)

    assert status_a == "created"
    assert status_b == "created"
    assert doc_a.id != doc_b.id
    assert get_by_path(session, "docs/intro.md").id == doc_a.id
    assert get_by_path(session, "posts/intro.md").id == doc_b.id


def test_path_is_primary_identity_not_slug(session):
    """A document committed again with the same path but a different slug updates the same record."""
    data = _make_staged(slug="old-slug", path="docs/stable.md", markdown="# v1")
    doc, _ = commit_doc(session, data)

    data2 = _make_staged(slug="new-slug", path="docs/stable.md", markdown="# v2")
    doc2, status = commit_doc(session, data2)

    assert status == "updated"
    assert doc2.id == doc.id
    assert doc2.slug == "new-slug"


# --- _replace_sections ---

def test_replace_sections_clears_old(session, doc):
    """_replace_sections deletes prior sections/blocks before inserting new ones."""
    sec = Section(document_id=doc.id, hash=sha256("initial"), position=0)
    session.add(sec)
    session.flush()
    blk = SectionBlock(
        id=uuid4(), section_id=sec.id,
        content="initial", hash=sha256("initial"),
        type=SectionBlockEnum.paragraph, position=0.0,
    )
    session.add(blk)
    session.flush()

    new_sections = [
        {"hash": sha256("replacement"), "position": 0, "blocks": [
            {"content": "replacement", "hash": sha256("replacement"),
             "type": SectionBlockEnum.paragraph.value, "position": 0.0, "level": None}
        ]}
    ]
    _replace_sections(session, doc.id, new_sections)

    all_sections = session.exec(select(Section).where(Section.document_id == doc.id)).all()
    assert len(all_sections) == 1
    assert all_sections[0].hash == sha256("replacement")
