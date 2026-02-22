"""Unit tests for core/parse.py"""

import pytest
from pathlib import Path

from mdpub.core.parse import _strip_frontmatter, discover_files, parse_file
from mdpub.core.models import ParsedDoc


def test_strip_frontmatter_with_yaml():
    """_strip_frontmatter extracts YAML header and returns body."""
    text = "---\ntitle: Hello\n---\n# Body\n"
    fm, body = _strip_frontmatter(text)
    assert fm == {"title": "Hello"}
    assert body == "# Body\n"


def test_strip_frontmatter_no_frontmatter():
    """_strip_frontmatter returns empty dict and full text when no header."""
    text = "# No frontmatter\n"
    fm, body = _strip_frontmatter(text)
    assert fm == {}
    assert body == text


def test_discover_files_single(tmp_path):
    """discover_files returns a list with one file when given a file path."""
    f = tmp_path / "doc.md"
    f.write_text("# Hello")
    assert discover_files(f) == [f]


def test_discover_files_non_md_skipped(tmp_path):
    """discover_files ignores non-.md/.mdx files."""
    (tmp_path / "notes.txt").write_text("text")
    assert discover_files(tmp_path) == []


def test_discover_files_dir(tmp_path):
    """discover_files finds all .md and .mdx files recursively."""
    (tmp_path / "a.md").write_text("a")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.mdx").write_text("b")
    files = discover_files(tmp_path)
    assert len(files) == 2


def test_parse_file_no_frontmatter(tmp_path):
    """parse_file produces a ParsedDoc with empty frontmatter."""
    f = tmp_path / "plain.md"
    f.write_text("# Hello\n\nWorld.\n")
    doc = parse_file(f)
    assert isinstance(doc, ParsedDoc)
    assert doc.frontmatter == {}
    assert doc.slug == "plain"


def test_parse_file_with_frontmatter(tmp_path):
    """parse_file extracts frontmatter into ParsedDoc.frontmatter."""
    f = tmp_path / "doc.md"
    f.write_text("---\ntitle: My Doc\n---\n# Body\n")
    doc = parse_file(f)
    assert doc.frontmatter == {"title": "My Doc"}
    assert "---" not in doc.markdown


def test_slug_from_frontmatter(tmp_path):
    """parse_file uses frontmatter slug field when present."""
    f = tmp_path / "anything.md"
    f.write_text("---\nslug: custom-slug\n---\n# Body\n")
    doc = parse_file(f)
    assert doc.slug == "custom-slug"


def test_slug_from_filename(tmp_path):
    """parse_file derives slug from filename stem when no frontmatter slug."""
    f = tmp_path / "My Document.md"
    f.write_text("# Body\n")
    doc = parse_file(f)
    assert doc.slug == "my-document"


def test_parse_file_hash_matches_raw(tmp_path):
    """parse_file hash is sha256 of full raw content including frontmatter."""
    from mdpub.core.utils.hashing import sha256
    f = tmp_path / "doc.md"
    raw = "---\ntitle: T\n---\n# Body\n"
    f.write_text(raw)
    doc = parse_file(f)
    assert doc.hash == sha256(raw)
    assert doc.raw_markdown == raw
