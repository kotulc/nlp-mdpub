"""Unit tests for crud/documents.py"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from mdpub.core.utils.hashing import sha256
from mdpub.crud.documents import (
    commit_doc, get_by_path, get_by_slug, _replace_sections,
    get_last_committed, get_by_collection, get_all_documents, list_collections,
)
from mdpub.crud.models import (
    Document, DocumentVersion, Section, SectionBlock, SectionBlockEnum,
    SectionMetric, SectionTag, Tag,
)


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


# --- committed_at ---

def test_commit_doc_sets_committed_at_on_create(session):
    """committed_at is set on newly created documents."""
    ts = datetime.now()
    data = _make_staged(slug="new-ts", path="docs/new-ts.md")
    doc, _ = commit_doc(session, data, committed_at=ts)
    assert doc.committed_at == ts


def test_commit_doc_sets_committed_at_on_update(session):
    """committed_at is updated when a document is updated."""
    ts1 = datetime(2026, 1, 1)
    data = _make_staged(slug="update-ts", path="docs/update-ts.md", markdown="# v1")
    doc, _ = commit_doc(session, data, committed_at=ts1)

    ts2 = datetime(2026, 2, 1)
    data2 = _make_staged(slug="update-ts", path="docs/update-ts.md", markdown="# v2")
    doc2, _ = commit_doc(session, data2, committed_at=ts2)
    assert doc2.committed_at == ts2


def test_commit_doc_does_not_update_committed_at_on_unchanged(session):
    """committed_at is not changed when a document is unchanged."""
    ts1 = datetime(2026, 1, 1)
    data = _make_staged(slug="stable-ts", path="docs/stable-ts.md")
    doc, _ = commit_doc(session, data, committed_at=ts1)

    ts2 = datetime(2026, 2, 1)
    doc2, status = commit_doc(session, data, committed_at=ts2)
    assert status == "unchanged"
    assert doc2.committed_at == ts1


# --- query helpers ---

def test_get_last_committed_returns_batch(session):
    """Returns only documents from the most recent commit batch."""
    ts1 = datetime(2026, 1, 1)
    ts2 = datetime(2026, 2, 1)
    commit_doc(session, _make_staged(slug="old", path="docs/old.md"), committed_at=ts1)
    commit_doc(session, _make_staged(slug="new", path="docs/new.md"), committed_at=ts2)

    result = get_last_committed(session)
    slugs = {d.slug for d in result}
    assert slugs == {"new"}


def test_get_last_committed_empty(session):
    """Returns [] when no documents have a committed_at timestamp."""
    result = get_last_committed(session)
    assert result == []


def test_get_by_collection_matches_prefix(session):
    """Returns docs whose path starts with the collection prefix."""
    commit_doc(session, _make_staged(slug="a", path="docs/a.md"))
    commit_doc(session, _make_staged(slug="b", path="docs/sub/b.md"))
    commit_doc(session, _make_staged(slug="c", path="posts/c.md"))

    result = get_by_collection(session, "docs")
    slugs = {d.slug for d in result}
    assert slugs == {"a", "b"}


def test_get_all_documents(session):
    """Returns all documents in the database."""
    commit_doc(session, _make_staged(slug="x", path="x.md"))
    commit_doc(session, _make_staged(slug="y", path="y.md"))
    assert len(get_all_documents(session)) == 2


def test_list_collections_distinct(session):
    """Returns sorted distinct top-level path components."""
    commit_doc(session, _make_staged(slug="a1", path="docs/a.md"))
    commit_doc(session, _make_staged(slug="a2", path="docs/b.md"))
    commit_doc(session, _make_staged(slug="p1", path="posts/p.md"))
    commit_doc(session, _make_staged(slug="r1", path="readme.md"))

    cols = list_collections(session)
    assert cols == [".", "docs", "posts"]


# --- metrics and tags ---

def _staged_with_enrichment(slug="enriched", path="enriched.md") -> dict:
    """Staged doc dict with a section that has metrics and tags."""
    return {
        "slug": slug,
        "path": path,
        "markdown": "# Hello\n",
        "hash": sha256("# Hello\n"),
        "frontmatter": {},
        "sections": [{
            "hash": sha256("# Hello"),
            "position": 0,
            "blocks": [{"content": "# Hello", "hash": sha256("# Hello"),
                        "type": "heading", "position": 0.0, "level": 1}],
            "metrics": {"sentiment": 0.8, "word_count": 5.0},
            "tags": ["nlp", "ml"],
        }],
    }


def test_commit_doc_writes_metrics(session):
    """commit_doc persists SectionMetric rows when metrics are present in staged data."""
    commit_doc(session, _staged_with_enrichment())
    metrics = session.exec(select(SectionMetric)).all()
    assert {m.name: m.value for m in metrics} == {"sentiment": 0.8, "word_count": 5.0}


def test_commit_doc_writes_tags(session):
    """commit_doc creates Tag and SectionTag rows when tags are present in staged data."""
    commit_doc(session, _staged_with_enrichment())
    tags = session.exec(select(Tag)).all()
    assert {t.name for t in tags} == {"nlp", "ml"}
    section_tags = session.exec(select(SectionTag)).all()
    assert len(section_tags) == 2


def test_commit_doc_tag_positions(session):
    """SectionTag rows are ordered by their position in the tags list."""
    commit_doc(session, _staged_with_enrichment())
    section_tags = sorted(session.exec(select(SectionTag)).all(), key=lambda t: t.position)
    assert [st.tag_name for st in section_tags] == ["nlp", "ml"]


def test_commit_doc_clears_metrics_on_update(session):
    """Re-committing a doc with changed content replaces its metrics."""
    commit_doc(session, _staged_with_enrichment())
    updated = _staged_with_enrichment()
    updated["hash"] = sha256("updated")
    updated["sections"][0]["metrics"] = {"toxicity": 0.1}
    commit_doc(session, updated)
    metrics = session.exec(select(SectionMetric)).all()
    assert [m.name for m in metrics] == ["toxicity"]


def test_replace_sections_reuses_existing_tag(session):
    """Tags that already exist in the Tag table are reused rather than duplicated."""
    session.add(Tag(name="nlp", category="existing"))
    session.flush()
    commit_doc(session, _staged_with_enrichment())
    tags = session.exec(select(Tag)).all()
    assert len(tags) == 2  # "nlp" reused, "ml" created
    nlp = session.get(Tag, "nlp")
    assert nlp.category == "existing"  # original category preserved
