"""Integration tests for the extract → commit → export pipeline.

Each test runs one pipeline step against the canonical document below and
asserts stable expected values. Read this file top-to-bottom as a reference
for what each stage produces with default settings.

Canonical document (pipeline-test.md)
--------------------------------------
    ---
    title: Pipeline Test
    date: 2026-01-15
    ---

    # Introduction

    An introductory paragraph.

    ## Details

    More detailed content.

Block layout after extract (4 blocks, flat, no hashes or positions):
    [heading h1]  "# Introduction"
    [paragraph]   "An introductory paragraph."
    [heading h2]  "## Details"
    [paragraph]   "More detailed content."

Section layout after commit with max_nesting=2 (default):
    Section 0:  [heading h1] + [paragraph]
    Section 1:  [heading h2] + [paragraph]

Section layout after commit with max_nesting=1:
    Section 0:  all 4 blocks  (h2 is below the nesting threshold)

Export output:
    Frontmatter: slug, title, date (+ tags/metrics if enriched; no sections array)
    Body:        reconstructed markdown blocks in section/position order
    No sidecar JSON file is produced.
"""

import json

import pytest
import yaml
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from mdpub.core.pipeline import run_commit, run_export, run_extract
from mdpub.crud.models import Section, SectionBlock


CANONICAL_MD = """\
---
title: Pipeline Test
date: 2026-01-15
---

# Introduction

An introductory paragraph.

## Details

More detailed content.
"""


# --- fixtures ---

@pytest.fixture(name="engine")
def engine_fixture():
    """Fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="staging_dir")
def staging_dir_fixture(tmp_path):
    return tmp_path / ".mdpub" / "staging"


@pytest.fixture(name="source_file")
def source_file_fixture(tmp_path):
    """Write the canonical document to a temp file."""
    f = tmp_path / "pipeline-test.md"
    f.write_text(CANONICAL_MD)
    return f


@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


# --- extract ---

def test_extract_staging_keys(source_file, staging_dir):
    """Staging JSON contains exactly: slug, path, markdown, frontmatter, content."""
    results = run_extract(str(source_file), "gfm-like", staging_dir)
    data = json.loads(results[0][1].read_text())
    assert set(data.keys()) == {"slug", "path", "markdown", "frontmatter", "content"}


def test_extract_slug_and_frontmatter(source_file, staging_dir):
    """slug is derived from filename; frontmatter values are preserved as strings."""
    results = run_extract(str(source_file), "gfm-like", staging_dir)
    data = json.loads(results[0][1].read_text())
    assert data["slug"] == "pipeline-test"
    assert data["frontmatter"]["title"] == "Pipeline Test"
    assert data["frontmatter"]["date"] == "2026-01-15"


def test_extract_block_count(source_file, staging_dir):
    """Canonical document produces exactly 4 flat content blocks."""
    results = run_extract(str(source_file), "gfm-like", staging_dir)
    data = json.loads(results[0][1].read_text())
    assert len(data["content"]) == 4


def test_extract_block_types_and_content(source_file, staging_dir):
    """Block types and content strings match the canonical document order."""
    results = run_extract(str(source_file), "gfm-like", staging_dir)
    blocks = json.loads(results[0][1].read_text())["content"]

    assert blocks[0]["type"] == "heading"
    assert blocks[0]["content"] == "# Introduction"
    assert blocks[1]["type"] == "paragraph"
    assert blocks[1]["content"] == "An introductory paragraph."
    assert blocks[2]["type"] == "heading"
    assert blocks[2]["content"] == "## Details"
    assert blocks[3]["type"] == "paragraph"
    assert blocks[3]["content"] == "More detailed content."


def test_extract_no_internal_fields(source_file, staging_dir):
    """Staging blocks contain no hash, position, or level fields."""
    results = run_extract(str(source_file), "gfm-like", staging_dir)
    blocks = json.loads(results[0][1].read_text())["content"]
    for b in blocks:
        assert "hash" not in b
        assert "position" not in b
        assert "level" not in b


# --- commit (max_nesting=2, default) ---

def test_commit_section_count_nesting_2(source_file, staging_dir, engine):
    """max_nesting=2 splits h1 and h2 into 2 separate sections."""
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=2, staging_dir=staging_dir)

    with Session(engine) as s:
        sections = s.exec(select(Section)).all()
    assert len(sections) == 2


def test_commit_blocks_per_section_nesting_2(source_file, staging_dir, engine):
    """With max_nesting=2 each section holds exactly 2 blocks (heading + paragraph)."""
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=2, staging_dir=staging_dir)

    with Session(engine) as s:
        sections = sorted(s.exec(select(Section)).all(), key=lambda s: s.position)
        for sec in sections:
            blocks = s.exec(select(SectionBlock).where(SectionBlock.section_id == sec.id)).all()
            assert len(blocks) == 2


# --- commit (max_nesting=1) ---

def test_commit_section_count_nesting_1(source_file, staging_dir, engine):
    """max_nesting=1 keeps all blocks in one section (h2 does not split)."""
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=1, staging_dir=staging_dir)

    with Session(engine) as s:
        sections = s.exec(select(Section)).all()
    assert len(sections) == 1


def test_commit_block_count_nesting_1(source_file, staging_dir, engine):
    """With max_nesting=1 the single section holds all 4 blocks."""
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=1, staging_dir=staging_dir)

    with Session(engine) as s:
        sections = s.exec(select(Section)).all()
        blocks = s.exec(select(SectionBlock)).all()
    assert len(sections) == 1
    assert len(blocks) == 4


# --- export ---

def _build_and_export(source_file, staging_dir, engine, tmp_path, fmt="mdx", max_nesting=2):
    """Run the full pipeline and return mdx_path."""
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=max_nesting, staging_dir=staging_dir)
    out = tmp_path / "dist"
    with Session(engine) as s:
        from mdpub.crud.models import Document
        docs = s.exec(select(Document)).all()
        results = run_export(s, docs, out, fmt)
    _, mdx_path = results[0]
    return mdx_path


def test_export_mdx_frontmatter(source_file, staging_dir, engine, tmp_path):
    """Exported MDX frontmatter contains slug and user fields; no doc_id, hash, or sections."""
    mdx_path = _build_and_export(source_file, staging_dir, engine, tmp_path)
    fm = yaml.safe_load(mdx_path.read_text().split("---\n")[1])
    assert fm["slug"] == "pipeline-test"
    assert fm["title"] == "Pipeline Test"
    assert fm["date"] == "2026-01-15"
    assert "doc_id" not in fm
    assert "hash" not in fm
    assert "sections" not in fm


def test_export_mdx_body_content(source_file, staging_dir, engine, tmp_path):
    """Exported MDX body is reconstructed from DB blocks in section/position order."""
    mdx_path = _build_and_export(source_file, staging_dir, engine, tmp_path)
    body = mdx_path.read_text().split("---\n\n", 1)[1]
    assert "# Introduction" in body
    assert "An introductory paragraph." in body
    assert "## Details" in body
    assert "More detailed content." in body


def test_export_no_json_sidecar(source_file, staging_dir, engine, tmp_path):
    """Export produces no .json sidecar file alongside the .mdx."""
    mdx_path = _build_and_export(source_file, staging_dir, engine, tmp_path)
    assert not mdx_path.with_suffix(".json").exists()


def test_export_md_format(source_file, staging_dir, engine, tmp_path):
    """output_format=md produces a .md file instead of .mdx."""
    mdx_path = _build_and_export(source_file, staging_dir, engine, tmp_path, fmt="md")
    assert mdx_path.suffix == ".md"
    assert mdx_path.exists()


# --- config-effect tests ---
#
# Canonical staging JSON used below includes 3 tags and 3 metrics on each block
# so that max_tags / max_metrics limits are easy to verify against a known count.

ENRICHED_STAGING = """\
{
  "slug": "enriched",
  "path": "enriched.md",
  "markdown": "# Intro\\n\\nBody.",
  "frontmatter": {},
  "content": [
    {
      "type": "heading",
      "content": "# Intro",
      "tags": {"alpha": 0.9, "beta": 0.8, "gamma": 0.7},
      "metrics": {"a": 1.0, "b": 2.0, "c": 3.0}
    },
    {
      "type": "paragraph",
      "content": "Body.",
      "tags": {},
      "metrics": {}
    }
  ]
}
"""


def _commit_enriched(staging_dir, engine, max_nesting=2):
    """Write the enriched staging file and commit it; return the engine."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    (staging_dir / "enriched.json").write_text(ENRICHED_STAGING)
    run_commit(engine, max_versions=10, max_nesting=max_nesting, staging_dir=staging_dir)
    return engine


def _export_enriched(engine, tmp_path, max_tags=0, max_metrics=0):
    """Export the committed enriched doc; return the frontmatter dict from the .mdx file."""
    out = tmp_path / "dist"
    with Session(engine) as s:
        from mdpub.crud.models import Document
        docs = s.exec(select(Document)).all()
        results = run_export(s, docs, out, "mdx", max_tags=max_tags, max_metrics=max_metrics)
    _, mdx_path = results[0]
    return yaml.safe_load(mdx_path.read_text().split("---\n")[1])


def test_max_nesting_1_produces_one_section(source_file, staging_dir, engine):
    """max_nesting=1 keeps h2 inside the h1 section — canonical doc produces 1 section."""
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=1, staging_dir=staging_dir)
    with Session(engine) as s:
        sections = s.exec(select(Section)).all()
    assert len(sections) == 1


def test_max_nesting_2_produces_two_sections(source_file, staging_dir, engine):
    """max_nesting=2 splits h1 and h2 into 2 sections (canonical document)."""
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=2, staging_dir=staging_dir)
    with Session(engine) as s:
        sections = s.exec(select(Section)).all()
    assert len(sections) == 2


def test_max_tags_limits_output(staging_dir, engine, tmp_path):
    """max_tags=2 truncates the doc-level tags dict to 2 entries in the exported frontmatter."""
    _commit_enriched(staging_dir, engine)
    fm = _export_enriched(engine, tmp_path, max_tags=2)
    assert len(fm["tags"]) <= 2


def test_max_tags_zero_is_unlimited(staging_dir, engine, tmp_path):
    """max_tags=0 (default) exports all 3 tags without truncation."""
    _commit_enriched(staging_dir, engine)
    fm = _export_enriched(engine, tmp_path, max_tags=0)
    assert len(fm["tags"]) == 3


def test_max_metrics_limits_output(staging_dir, engine, tmp_path):
    """max_metrics=1 truncates the doc-level metrics dict to 1 entry."""
    _commit_enriched(staging_dir, engine)
    fm = _export_enriched(engine, tmp_path, max_metrics=1)
    assert len(fm["metrics"]) == 1


def test_config_env_max_nesting(source_file, staging_dir, engine, monkeypatch):
    """MDPUB_MAX_NESTING=1 env var causes commit to produce 1 section for the canonical doc."""
    monkeypatch.setenv("MDPUB_MAX_NESTING", "1")
    from mdpub.config import load_config
    settings = load_config()
    run_extract(str(source_file), "gfm-like", staging_dir)
    run_commit(engine, max_versions=10, max_nesting=settings.max_nesting, staging_dir=staging_dir)
    with Session(engine) as s:
        sections = s.exec(select(Section)).all()
    assert len(sections) == 1
