"""Document and section persistence: upsert, section replacement, path/slug lookup"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func
from sqlmodel import Session, select

from mdpub.crud.models import Document, Section, SectionBlock, SectionBlockEnum
from mdpub.crud.versioning import save_version


def get_by_path(session: Session, path: str) -> Document | None:
    """Return the Document with the given source path, or None if not found."""
    return session.exec(select(Document).where(Document.path == path)).one_or_none()


def get_by_slug(session: Session, slug: str) -> Document | None:
    """Return the first Document with the given slug, or None if not found."""
    return session.exec(select(Document).where(Document.slug == slug)).first()


def get_last_committed(session: Session) -> list[Document]:
    """Return documents from the most recent commit batch (MAX committed_at)."""
    max_ts = session.exec(select(func.max(Document.committed_at))).one()
    if max_ts is None:
        return []
    return list(session.exec(select(Document).where(Document.committed_at == max_ts)).all())


def get_by_collection(session: Session, collection: str) -> list[Document]:
    """Return documents whose path falls under the given top-level directory.

    '.' matches root-level documents (no parent directory).
    Any other value matches documents whose first path component equals collection.
    """
    all_docs = session.exec(select(Document)).all()
    result = []
    for doc in all_docs:
        parts = Path(doc.path).parts
        top = parts[0] if len(parts) > 1 else '.'
        if top == collection:
            result.append(doc)
    return result


def get_all_documents(session: Session) -> list[Document]:
    """Return all documents in the database."""
    return list(session.exec(select(Document)).all())


def list_collections(session: Session) -> list[str]:
    """Return sorted distinct top-level path components across all stored documents."""
    paths = session.exec(select(Document.path)).all()
    seen: set[str] = set()
    result: list[str] = []
    for p in paths:
        parts = Path(p).parts
        top = parts[0] if len(parts) > 1 else '.'
        if top not in seen:
            seen.add(top)
            result.append(top)
    return sorted(result)


def _replace_sections(session: Session, doc_id, sections: list[dict]) -> None:
    """Delete all existing sections/blocks for a document and insert new ones."""
    existing = session.exec(select(Section).where(Section.document_id == doc_id)).all()
    for s in existing:
        for b in session.exec(select(SectionBlock).where(SectionBlock.section_id == s.id)).all():
            session.delete(b)
        session.delete(s)
    session.flush()

    for sec in sections:
        section = Section(document_id=doc_id, hash=sec['hash'], position=sec['position'])
        session.add(section)
        session.flush()
        for blk in sec['blocks']:
            session.add(SectionBlock(
                id=uuid4(),
                section_id=section.id,
                content=blk['content'],
                hash=blk['hash'],
                type=SectionBlockEnum(blk['type']),
                position=blk['position'],
                level=blk.get('level'),
            ))
    session.flush()


def commit_doc(
    session: Session,
    data: dict,
    max_versions: int = 10,
    committed_at: datetime | None = None,
    ) -> tuple[Document, str]:
    """Upsert a staged ExtractedDoc dict.

    Returns (doc, status) where status is 'created', 'updated', or 'unchanged'.
    Flushes but does not commit — caller controls the transaction.
    committed_at is set on created/updated docs only; unchanged docs are skipped.
    """
    doc = get_by_path(session, data['path'])

    if doc:
        if doc.hash == data['hash']:
            return doc, 'unchanged'
        save_version(session, doc, max_versions)
        doc.slug = data['slug']
        doc.markdown = data['markdown']
        doc.hash = data['hash']
        doc.frontmatter = data['frontmatter'] or None
        doc.path = data['path']
        doc.updated_at = datetime.now()
        doc.committed_at = committed_at
        session.add(doc)
        session.flush()
        _replace_sections(session, doc.id, data['sections'])
        return doc, 'updated'

    doc = Document(
        slug=data['slug'],
        markdown=data['markdown'],
        hash=data['hash'],
        frontmatter=data['frontmatter'] or None,
        path=data['path'],
        committed_at=committed_at,
    )
    session.add(doc)
    session.flush()
    _replace_sections(session, doc.id, data['sections'])
    return doc, 'created'
