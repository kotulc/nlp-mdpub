"""Document version persistence: save, prune, list, diff, and revert operations"""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from mdpub.crud.tables import Document, DocumentVersion
from mdpub.core.utils.diff import unified_diff


def diff_versions(session: Session, document_id: UUID, from_num: int, to_num: int, context: int = 3) -> list[str]:
    """Unified diff lines between two stored versions. Raises ValueError if either is missing."""
    def _get(num: int) -> DocumentVersion:
        v = session.exec(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .where(DocumentVersion.version_num == num)
        ).one_or_none()
        if v is None:
            raise ValueError(f"Version {num} not found for document {document_id}")
        return v

    v_from, v_to = _get(from_num), _get(to_num)
    return unified_diff(v_from.markdown, v_to.markdown, f"v{from_num}", f"v{to_num}", context)


def list_versions(session: Session, document_id: UUID) -> list[DocumentVersion]:
    """Return all versions for a document ordered by version_num ascending."""
    return list(
        session.exec(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_num.asc())
        ).all()
    )


def prune_versions(session: Session, document_id: UUID, max_versions: int) -> int:
    """Delete oldest versions beyond max_versions. Returns count deleted. No-op if max_versions=0."""
    if max_versions == 0:
        return 0

    versions = session.exec(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_num.asc())
    ).all()

    excess = len(versions) - max_versions
    if excess <= 0:
        return 0

    for v in versions[:excess]:
        session.delete(v)
    session.flush()

    return excess


def revert_to_version(session: Session, doc: Document, version_num: int, max_versions: int = 10) -> Document:
    """Promote a prior version's content as a new commit on the current Document.

    Snapshots the current Document state first (so it becomes part of history),
    then overwrites doc fields with the target version's content.
    Flushes but does not commit — caller controls the transaction.
    Raises ValueError if version_num is not found for this document.
    """
    target = session.exec(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .where(DocumentVersion.version_num == version_num)
    ).one_or_none()

    if target is None:
        raise ValueError(f"Version {version_num} not found for document {doc.id}")

    save_version(session, doc, max_versions=max_versions)

    doc.markdown = target.markdown
    doc.hash = target.hash
    doc.frontmatter = json.loads(target.frontmatter) if target.frontmatter else None
    doc.updated_at = datetime.now()
    session.add(doc)
    session.flush()

    return doc


def save_version(session: Session, doc: Document, max_versions: int = 10) -> DocumentVersion:
    """Snapshot current Document state as a new immutable version.

    Computes next version_num as MAX(version_num)+1 for this document.
    Calls prune_versions after saving if max_versions > 0.
    """
    result = session.exec(
        select(func.max(DocumentVersion.version_num))
        .where(DocumentVersion.document_id == doc.id)
    ).one()

    version = DocumentVersion(
        document_id=doc.id,
        version_num=(result or 0) + 1,
        markdown=doc.markdown,
        hash=doc.hash,
        frontmatter=json.dumps(doc.frontmatter) if doc.frontmatter is not None else None,
    )
    session.add(version)
    session.flush()

    if max_versions > 0:
        prune_versions(session, doc.id, max_versions)

    return version
