"""Unit tests for crud/versioning.py"""

import json
import pytest
from sqlmodel import Session, select

from mdpub.core.utils.hashing import sha256
from mdpub.crud.tables import Document, DocumentVersion
from mdpub.crud.versioning import (
    diff_versions, list_versions, prune_versions, revert_to_version, save_version
)


# --- helpers ---

def _make_version(session: Session, doc: Document, markdown: str) -> DocumentVersion:
    """Mutate doc.markdown + hash and save a version snapshot."""
    doc.markdown = markdown
    doc.hash = sha256(markdown)
    return save_version(session, doc, max_versions=0)


# --- save_version ---

def test_save_version_creates_record(session, doc):
    """save_version creates a DocumentVersion row."""
    v = save_version(session, doc)
    assert session.get(DocumentVersion, v.id) is not None


def test_save_version_first_num_is_one(session, doc):
    """save_version assigns version_num=1 to the first snapshot."""
    v = save_version(session, doc)
    assert v.version_num == 1


def test_save_version_increments_num(session, doc):
    """save_version increments version_num on each call."""
    v1 = save_version(session, doc, max_versions=0)
    v2 = save_version(session, doc, max_versions=0)
    assert v2.version_num == v1.version_num + 1


@pytest.mark.parametrize("frontmatter,expect_stored", [
    ({"title": "Test", "tags": ["a"]}, True),
    (None, False),
])
def test_save_version_frontmatter(session, doc, frontmatter, expect_stored):
    """save_version serializes dict frontmatter to JSON string; None stays NULL."""
    doc.frontmatter = frontmatter
    v = save_version(session, doc, max_versions=0)
    if expect_stored:
        assert v.frontmatter == json.dumps(frontmatter)
    else:
        assert v.frontmatter is None


def test_save_version_prunes_on_overflow(session, doc):
    """save_version prunes oldest versions when count exceeds max_versions."""
    for _ in range(5):
        save_version(session, doc, max_versions=3)
    assert len(list_versions(session, doc.id)) == 3


def test_save_version_no_prune_when_disabled(session, doc):
    """save_version does not prune when max_versions=0."""
    for _ in range(5):
        save_version(session, doc, max_versions=0)
    assert len(list_versions(session, doc.id)) == 5


# --- prune_versions ---

@pytest.mark.parametrize("n_saves,max_v,expected_remaining,expected_deleted", [
    (5, 3, 3, 2),
    (3, 5, 3, 0),
    (5, 0, 5, 0),
])
def test_prune_versions(session, doc, n_saves, max_v, expected_remaining, expected_deleted):
    """prune_versions keeps the N newest versions and deletes the oldest."""
    for _ in range(n_saves):
        save_version(session, doc, max_versions=0)
    deleted = prune_versions(session, doc.id, max_v)
    assert deleted == expected_deleted
    assert len(list_versions(session, doc.id)) == expected_remaining


def test_prune_versions_keeps_newest(session, doc):
    """prune_versions deletes lowest version_nums, preserving the highest."""
    for _ in range(4):
        save_version(session, doc, max_versions=0)
    prune_versions(session, doc.id, 2)
    remaining = list_versions(session, doc.id)
    assert [v.version_num for v in remaining] == [3, 4]


# --- list_versions ---

def test_list_versions_empty(session, doc):
    """list_versions returns an empty list when no versions exist."""
    assert list_versions(session, doc.id) == []


def test_list_versions_ordered(session, doc):
    """list_versions returns versions in ascending version_num order."""
    for _ in range(3):
        save_version(session, doc, max_versions=0)
    nums = [v.version_num for v in list_versions(session, doc.id)]
    assert nums == sorted(nums)


def test_list_versions_isolates_by_doc(session, doc):
    """list_versions only returns versions for the given document_id."""
    other = Document(slug="other-doc", markdown="other", hash=sha256("other"), path="docs/other-doc.md")
    session.add(other)
    session.flush()
    save_version(session, doc, max_versions=0)
    save_version(session, other, max_versions=0)
    assert all(v.document_id == doc.id for v in list_versions(session, doc.id))


# --- diff_versions ---

def test_diff_versions_returns_lines(session, doc):
    """diff_versions returns non-empty diff lines for differing content."""
    _make_version(session, doc, "# Hello\n\nWorld")
    _make_version(session, doc, "# Hello\n\nChanged")
    lines = diff_versions(session, doc.id, 1, 2)
    assert len(lines) > 0


def test_diff_versions_identical_content(session, doc):
    """diff_versions returns an empty list when both versions have identical content."""
    _make_version(session, doc, "# Same\n")
    _make_version(session, doc, "# Same\n")
    assert diff_versions(session, doc.id, 1, 2) == []


@pytest.mark.parametrize("from_num,to_num", [(1, 99), (99, 1)])
def test_diff_versions_raises_on_missing(session, doc, from_num, to_num):
    """diff_versions raises ValueError when a requested version_num does not exist."""
    save_version(session, doc, max_versions=0)
    with pytest.raises(ValueError):
        diff_versions(session, doc.id, from_num, to_num)


# --- revert_to_version ---

def test_revert_to_version_updates_doc(session, doc):
    """revert_to_version overwrites doc fields with content from the target version."""
    original_markdown = doc.markdown
    save_version(session, doc, max_versions=0)
    doc.markdown = "# Updated\n"
    doc.hash = sha256("# Updated\n")
    revert_to_version(session, doc, version_num=1)
    assert doc.markdown == original_markdown


def test_revert_to_version_snapshots_current(session, doc):
    """revert_to_version saves the current doc as a new version before reverting."""
    save_version(session, doc, max_versions=0)
    count_before = len(list_versions(session, doc.id))
    revert_to_version(session, doc, version_num=1)
    assert len(list_versions(session, doc.id)) == count_before + 1


def test_revert_to_version_refreshes_updated_at(session, doc):
    """revert_to_version sets doc.updated_at to a new timestamp."""
    original_updated_at = doc.updated_at
    save_version(session, doc, max_versions=0)
    revert_to_version(session, doc, version_num=1)
    assert doc.updated_at >= original_updated_at


def test_revert_to_version_raises_on_missing(session, doc):
    """revert_to_version raises ValueError when version_num does not exist."""
    with pytest.raises(ValueError):
        revert_to_version(session, doc, version_num=99)
