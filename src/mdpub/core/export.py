"""Export pipeline: build MDX/MD content, sidecar JSON, and write output files"""

import json
from pathlib import Path

import yaml
from sqlmodel import Session, select

from mdpub.crud.models import Document, DocumentVersion, Section, SectionBlock
from mdpub.crud.versioning import list_versions


def build_mdx(doc: Document, fmt: str = 'mdx') -> str:
    """Return doc.markdown with a merged YAML frontmatter block prepended."""
    fm = dict(doc.frontmatter or {})
    fm['slug'] = doc.slug
    fm['doc_id'] = str(doc.id)
    fm['hash'] = doc.hash
    body = doc.markdown.lstrip('\n')
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{header}---\n\n{body}"


def build_sidecar(
    doc: Document,
    sections: list[Section],
    blocks_by_section: dict,
    versions: list[DocumentVersion],
    ) -> dict:
    """Build the sidecar JSON dict for a document."""
    return {
        "slug": doc.slug,
        "doc_id": str(doc.id),
        "path": doc.path,
        "hash": doc.hash,
        "committed_at": doc.committed_at.isoformat() if doc.committed_at else None,
        "frontmatter": doc.frontmatter or {},
        "sections": [
            {
                "position": s.position,
                "hash": s.hash,
                "blocks": [
                    {
                        "type": b.type.value,
                        "content": b.content,
                        "hash": b.hash,
                        "position": b.position,
                        "level": b.level,
                    }
                    for b in sorted(blocks_by_section.get(s.id, []), key=lambda b: b.position)
                ],
            }
            for s in sorted(sections, key=lambda s: s.position)
        ],
        "versions": [
            {
                "version_num": v.version_num,
                "hash": v.hash,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ],
    }


def write_doc(
    doc: Document,
    session: Session,
    output_dir: Path,
    fmt: str = 'mdx',
    ) -> tuple[Path, Path]:
    """Write MDX/MD + sidecar JSON for a single document.

    Output path mirrors the source directory structure:
      output_dir / Path(doc.path).parent / doc.slug.{fmt|json}

    Returns (mdx_path, json_path).
    """
    src = Path(doc.path)
    dest_dir = output_dir / src.parent
    dest_dir.mkdir(parents=True, exist_ok=True)

    sections = session.exec(select(Section).where(Section.document_id == doc.id)).all()
    blocks_by_section: dict = {}
    for s in sections:
        blocks_by_section[s.id] = session.exec(
            select(SectionBlock).where(SectionBlock.section_id == s.id)
        ).all()
    versions = list_versions(session, doc.id)

    mdx_path = dest_dir / f"{doc.slug}.{fmt}"
    json_path = dest_dir / f"{doc.slug}.json"

    mdx_path.write_text(build_mdx(doc, fmt), encoding='utf-8')
    json_path.write_text(
        json.dumps(build_sidecar(doc, sections, blocks_by_section, versions), indent=2),
        encoding='utf-8',
    )
    return mdx_path, json_path
