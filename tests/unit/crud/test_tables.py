"""Unit tests for crud/tables.py — validates schema definitions and constraints"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel
from uuid import uuid4

from mdpub.core.utils.hashing import sha256
from mdpub.crud.tables import (
    Document, DocumentMeta, DocumentVersion, Section, SectionBlock, SectionBlockEnum
)


EXPECTED_TABLES = {
    "documents", "document_meta", "document_versions",
    "sections", "section_blocks", "section_metrics", "section_tags", "tags",
}


def test_all_tables_created(engine):
    """All expected tables are present after SQLModel.metadata.create_all."""
    assert EXPECTED_TABLES.issubset(set(SQLModel.metadata.tables.keys()))


def test_document_insert(session, doc):
    """Document is inserted with a generated UUID and correct slug."""
    assert doc.id is not None
    assert doc.slug == "test-doc"


def test_document_slug_unique(session, doc):
    """Document raises IntegrityError on duplicate slug."""
    session.add(Document(slug="test-doc", markdown="other", hash=sha256("other")))
    with pytest.raises(IntegrityError):
        session.flush()


def test_document_version_insert(session, doc):
    """DocumentVersion is inserted with a generated UUID."""
    v = DocumentVersion(document_id=doc.id, version_num=1, markdown=doc.markdown, hash=doc.hash)
    session.add(v)
    session.flush()
    assert v.id is not None


def test_document_version_unique_constraint(session, doc):
    """DocumentVersion raises IntegrityError on duplicate (document_id, version_num)."""
    session.add(DocumentVersion(document_id=doc.id, version_num=1, markdown="a", hash=sha256("a")))
    session.flush()
    session.add(DocumentVersion(document_id=doc.id, version_num=1, markdown="b", hash=sha256("b")))
    with pytest.raises(IntegrityError):
        session.flush()


def test_document_meta_composite_pk(session, doc):
    """DocumentMeta raises IntegrityError on duplicate (document_id, key)."""
    session.add(DocumentMeta(document_id=doc.id, key="title", value="A"))
    session.flush()
    session.add(DocumentMeta(document_id=doc.id, key="title", value="B"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_section_block_enum_values(session, doc):
    """SectionBlock accepts all SectionBlockEnum values without error."""
    sect = Section(document_id=doc.id, hash=sha256("s"), position=0)
    session.add(sect)
    session.flush()
    for block_type in SectionBlockEnum:
        session.add(SectionBlock(
            id=uuid4(), section_id=sect.id,
            content="x", hash=sha256("x"), type=block_type, position=0.0
        ))
    session.flush()
