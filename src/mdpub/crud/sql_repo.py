from __future__ import annotations
from datetime import datetime
from sqlmodel import Session, select

from mdpub.parser.models import StructuredDocument, Frontmatter, Block
from mdpub.crud.repo import DocumentRepo
from mdpub.crud.sql_models import DocumentRow

def _row_to_doc(r: DocumentRow) -> StructuredDocument:
    return StructuredDocument(
        doc_id=r.doc_id,
        source_path=r.source_path,
        slug=r.slug,
        created_at=r.created_at,
        updated_at=r.updated_at,
        frontmatter=Frontmatter(raw=r.frontmatter),
        blocks=[Block(**b) for b in (r.blocks or [])],
        content_hash=r.content_hash,
        tags=list(r.tags or []),
        metrics=dict(r.metrics or {}),
    )

def _doc_to_row(doc: StructuredDocument, existing: DocumentRow | None) -> DocumentRow:
    row = existing or DocumentRow(source_path=doc.source_path, doc_id=doc.doc_id, content_hash=doc.content_hash)
    row.doc_id = doc.doc_id
    row.slug = doc.slug
    row.content_hash = doc.content_hash
    row.updated_at = datetime.utcnow()
    if existing is None:
        row.created_at = doc.created_at
    row.frontmatter = doc.frontmatter.raw
    row.blocks = [b.model_dump() for b in doc.blocks]
    row.tags = doc.tags
    row.metrics = doc.metrics
    return row

class SQLRepo(DocumentRepo):
    def __init__(self, session: Session):
        self.session = session

    def get_by_source_path(self, source_path: str) -> StructuredDocument | None:
        row = self.session.exec(select(DocumentRow).where(DocumentRow.source_path == source_path)).first()
        return _row_to_doc(row) if row else None

    def upsert_by_source_path(self, doc: StructuredDocument) -> tuple[StructuredDocument, bool]:
        row = self.session.exec(select(DocumentRow).where(DocumentRow.source_path == doc.source_path)).first()
        if row and row.content_hash == doc.content_hash:
            return _row_to_doc(row), False

        row2 = _doc_to_row(doc, existing=row)
        self.session.add(row2)
        self.session.commit()
        self.session.refresh(row2)
        return _row_to_doc(row2), True
