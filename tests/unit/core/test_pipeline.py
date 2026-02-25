"""Unit tests for core/pipeline.py"""

import datetime
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from mdpub.core.pipeline import run_commit, run_export, run_extract
from mdpub.core.utils.hashing import sha256
from mdpub.crud.models import Document


@pytest.fixture(name="engine")
def engine_fixture():
    """In-memory SQLite engine with all tables created."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture(name="staging_dir")
def staging_dir_fixture(tmp_path):
    return tmp_path / ".mdpub" / "staging"


@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path, monkeypatch):
    """Run each test from a clean tmp directory so relative paths are isolated."""
    monkeypatch.chdir(tmp_path)


# --- run_extract ---

def test_run_extract_writes_staging(tmp_path, staging_dir):
    """run_extract writes one JSON file per parsed document to staging_dir."""
    (tmp_path / "hello.md").write_text("# Hello\n\nWorld\n")
    run_extract("hello.md", "gfm-like", staging_dir)
    assert any(staging_dir.glob("*.json"))


def test_run_extract_returns_pairs(tmp_path, staging_dir):
    """run_extract returns one (source_path, staging_file) pair per document."""
    (tmp_path / "hello.md").write_text("# Hello\n\nWorld\n")
    results = run_extract("hello.md", "gfm-like", staging_dir)
    assert len(results) == 1
    src, out_file = results[0]
    assert "hello" in str(src)
    assert out_file.suffix == ".json"
    assert out_file.exists()


def test_run_extract_staging_json_is_valid(tmp_path, staging_dir):
    """Staging files written by run_extract are valid JSON with expected keys."""
    (tmp_path / "doc.md").write_text("# Doc\n\nContent.\n")
    results = run_extract("doc.md", "gfm-like", staging_dir)
    _, out_file = results[0]
    data = json.loads(out_file.read_text())
    assert "slug" in data
    assert "content" in data


@pytest.mark.parametrize("frontmatter,field,expected", [
    ("date: 2026-01-15\n",     "date",     "2026-01-15"),
    ("updated: 2026-01-15T10:30:00\n", "updated", "2026-01-15T10:30:00"),
])
def test_run_extract_serializes_date_frontmatter(tmp_path, staging_dir, frontmatter, field, expected):
    """run_extract converts date/datetime frontmatter values to ISO strings in staging JSON."""
    (tmp_path / "post.md").write_text(f"---\n{frontmatter}---\n\n# Post\n\nBody.\n")
    results = run_extract("post.md", "gfm-like", staging_dir)
    _, out_file = results[0]
    data = json.loads(out_file.read_text())
    assert data["frontmatter"][field] == expected


def test_run_extract_raises_with_file_context_on_error(tmp_path, staging_dir, monkeypatch):
    """run_extract wraps per-document failures with the source file path."""
    (tmp_path / "bad.md").write_text("# Bad\n\nContent.\n")
    from mdpub.core import pipeline
    monkeypatch.setattr(pipeline, "extract_doc", lambda *a: (_ for _ in ()).throw(ValueError("oops")))
    with pytest.raises(RuntimeError, match="bad.md"):
        run_extract("bad.md", "gfm-like", staging_dir)


def test_run_extract_raises_on_invalid_frontmatter(tmp_path, staging_dir):
    """run_extract wraps YAML parse errors with the source file path."""
    (tmp_path / "bad.md").write_text("---\nis this even a key?\n---\n# Body\n")
    with pytest.raises(RuntimeError, match="bad.md"):
        run_extract("bad.md", "gfm-like", staging_dir)


# --- run_commit ---

def test_run_commit_returns_empty_on_no_staging(engine, staging_dir):
    """run_commit returns ({}, []) when no staging files exist."""
    counts, changes = run_commit(engine, max_versions=10, max_nesting=6, staging_dir=staging_dir)
    assert counts == {}
    assert changes == []


def test_run_commit_creates_docs(tmp_path, engine, staging_dir):
    """run_commit upserts staged docs and returns correct counts."""
    (tmp_path / "note.md").write_text("# Note\n\nBody.\n")
    run_extract("note.md", "gfm-like", staging_dir)
    counts, changes = run_commit(engine, max_versions=10, max_nesting=6, staging_dir=staging_dir)
    assert counts["created"] == 1
    assert counts["updated"] == 0
    assert any(status == "created" for status, _ in changes)


def test_run_commit_unchanged_on_rerun(tmp_path, engine, staging_dir):
    """run_commit returns unchanged status when doc content has not changed."""
    (tmp_path / "note.md").write_text("# Note\n\nBody.\n")
    run_extract("note.md", "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=6, staging_dir=staging_dir)
    counts, changes = run_commit(engine, max_versions=10, max_nesting=6, staging_dir=staging_dir)
    assert counts["unchanged"] == 1
    assert changes == []


# --- run_export ---

def _make_committed_doc(session, slug="export-doc", path="export-doc.md") -> Document:
    """Helper: insert a committed Document into the session."""
    from datetime import datetime
    doc = Document(
        slug=slug,
        markdown="# Hello\n\nWorld",
        hash=sha256("# Hello\n\nWorld"),
        path=path,
        committed_at=datetime(2026, 1, 1),
    )
    session.add(doc)
    session.flush()
    return doc


def test_run_export_returns_slug_path_pairs(session, tmp_path):
    """run_export returns one (slug, mdx_path) pair per document."""
    doc = _make_committed_doc(session)
    results = run_export(session, [doc], tmp_path, "mdx")
    assert len(results) == 1
    slug, mdx_path = results[0]
    assert slug == "export-doc"
    assert mdx_path.suffix == ".mdx"


def test_run_export_writes_files(session, tmp_path):
    """run_export produces both .mdx and .json files on disk."""
    doc = _make_committed_doc(session)
    run_export(session, [doc], tmp_path, "mdx")
    assert (tmp_path / "export-doc.mdx").exists()
    assert (tmp_path / "export-doc.json").exists()


def test_run_export_mirrors_source_dir(session, tmp_path):
    """Output directory mirrors the source file's parent path."""
    doc = _make_committed_doc(session, slug="guide", path="docs/guide.md")
    results = run_export(session, [doc], tmp_path, "mdx")
    _, mdx_path = results[0]
    assert mdx_path == tmp_path / "docs" / "guide.mdx"
