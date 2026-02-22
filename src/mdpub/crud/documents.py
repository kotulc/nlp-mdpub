"""Document and section persistence: upsert, section replacement, path/slug lookup"""

from datetime import datetime
from uuid import uuid4

from sqlmodel import Session, select

from mdpub.crud.models import Document, Section, SectionBlock, SectionBlockEnum
from mdpub.crud.versioning import save_version


def get_by_path(session: Session, path: str) -> Document | None:
    """Return the Document with the given source path, or None if not found."""
    return session.exec(select(Document).where(Document.path == path)).one_or_none()


def get_by_slug(session: Session, slug: str) -> Document | None:
    """Return the first Document with the given slug, or None if not found."""
    return session.exec(select(Document).where(Document.slug == slug)).first()


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
    ) -> tuple[Document, str]:
    """Upsert a staged ExtractedDoc dict.

    Returns (doc, status) where status is 'created', 'updated', or 'unchanged'.
    Flushes but does not commit — caller controls the transaction.
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
    )
    session.add(doc)
    session.flush()
    _replace_sections(session, doc.id, data['sections'])
    return doc, 'created'
