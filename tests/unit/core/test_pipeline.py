"""Unit tests for core/pipeline.py"""

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from mdpub.core.pipeline import STAGING, run_commit, run_export, run_extract
from mdpub.core.utils.hashing import sha256
from mdpub.crud.models import Document, SectionBlockEnum


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


@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path, monkeypatch):
    """Run each test from a clean tmp directory so STAGING is isolated."""
    monkeypatch.chdir(tmp_path)


# --- run_extract ---

def test_run_extract_writes_staging(tmp_path):
    """run_extract writes one JSON file per parsed document to STAGING."""
    (tmp_path / "hello.md").write_text("# Hello\n\nWorld\n")
    run_extract("hello.md", "gfm-like", 2)
    assert any(STAGING.glob("*.json"))


def test_run_extract_returns_pairs(tmp_path):
    """run_extract returns one (source_path, staging_file) pair per document."""
    (tmp_path / "hello.md").write_text("# Hello\n\nWorld\n")
    results = run_extract("hello.md", "gfm-like", 2)
    assert len(results) == 1
    src, out_file = results[0]
    assert "hello" in str(src)
    assert out_file.suffix == ".json"
    assert out_file.exists()


def test_run_extract_staging_json_is_valid(tmp_path):
    """Staging files written by run_extract are valid JSON with expected keys."""
    (tmp_path / "doc.md").write_text("# Doc\n\nContent.\n")
    results = run_extract("doc.md", "gfm-like", 2)
    _, out_file = results[0]
    data = json.loads(out_file.read_text())
    assert "slug" in data
    assert "sections" in data


# --- run_commit ---

def test_run_commit_returns_empty_on_no_staging(engine):
    """run_commit returns ({}, []) when no staging files exist."""
    counts, changes = run_commit(engine, max_versions=10)
    assert counts == {}
    assert changes == []


def test_run_commit_creates_docs(tmp_path, engine):
    """run_commit upserts staged docs and returns correct counts."""
    (tmp_path / "note.md").write_text("# Note\n\nBody.\n")
    run_extract("note.md", "gfm-like", 2)
    counts, changes = run_commit(engine, max_versions=10)
    assert counts["created"] == 1
    assert counts["updated"] == 0
    assert any(status == "created" for status, _ in changes)


def test_run_commit_unchanged_on_rerun(tmp_path, engine):
    """run_commit returns unchanged status when doc content has not changed."""
    (tmp_path / "note.md").write_text("# Note\n\nBody.\n")
    run_extract("note.md", "gfm-like", 2)
    run_commit(engine, max_versions=10)
    counts, changes = run_commit(engine, max_versions=10)
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
