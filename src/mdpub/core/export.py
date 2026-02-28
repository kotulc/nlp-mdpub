"""Export pipeline: build MDX/MD content, sidecar JSON, and write output files"""

import json
from pathlib import Path

import yaml
from sqlmodel import Session, select

from mdpub.crud.models import Document, Section, SectionBlock, SectionMetric, SectionTag


def build_body(sections: list[Section], blocks_by_section: dict) -> str:
    """Reconstruct markdown body from DB sections/blocks, skipping hidden sections."""
    parts = []
    for s in sorted(sections, key=lambda s: s.position):
        if s.hidden:
            continue
        blocks = sorted(blocks_by_section.get(s.id, []), key=lambda b: b.position)
        if blocks:
            parts.append("\n\n".join(b.content for b in blocks))
    return "\n\n".join(parts)


def build_mdx(doc: Document, body: str) -> str:
    """Return body with a merged YAML frontmatter block prepended (slug + user fields only)."""
    fm = dict(doc.frontmatter or {})
    fm['slug'] = doc.slug
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{header}---\n\n{body.lstrip()}"


def build_sidecar(
    doc: Document,
    sections: list[Section],
    tags_by_section: dict,
    metrics_by_section: dict,
    max_tags: int = 0,
    max_metrics: int = 0,
    ) -> dict:
    """Build the minimal sidecar JSON dict: slug, path, committed_at, frontmatter, sections.

    Each section entry contains only position, tags (ordered by SectionTag.position),
    and metrics. Hidden sections are excluded.
    max_tags / max_metrics limit entries per section (0 = unlimited).
    """
    tag_limit    = max_tags    or None
    metric_limit = max_metrics or None
    return {
        "slug": doc.slug,
        "path": doc.path,
        "committed_at": doc.committed_at.isoformat() if doc.committed_at else None,
        "frontmatter": doc.frontmatter or {},
        "sections": [
            {
                "position": s.position,
                "tags": [
                    st.tag_name
                    for st in sorted(tags_by_section.get(s.id, []), key=lambda t: t.position or 0)
                ][:tag_limit],
                "metrics": dict(
                    list({m.name: m.value for m in metrics_by_section.get(s.id, [])}.items())
                    [:metric_limit]
                ),
            }
            for s in sorted(sections, key=lambda s: s.position)
            if not s.hidden
        ],
    }


def write_doc(
    doc: Document,
    session: Session,
    output_dir: Path,
    fmt: str = 'mdx',
    max_tags: int = 0,
    max_metrics: int = 0,
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
    blocks_by_section = {
        s.id: session.exec(select(SectionBlock).where(SectionBlock.section_id == s.id)).all()
        for s in sections
    }
    tags_by_section = {
        s.id: session.exec(select(SectionTag).where(SectionTag.section_id == s.id)).all()
        for s in sections
    }
    metrics_by_section = {
        s.id: session.exec(select(SectionMetric).where(SectionMetric.section_id == s.id)).all()
        for s in sections
    }

    body = build_body(sections, blocks_by_section)
    mdx_path = dest_dir / f"{doc.slug}.{fmt}"
    json_path = dest_dir / f"{doc.slug}.json"

    mdx_path.write_text(build_mdx(doc, body), encoding='utf-8')
    json_path.write_text(
        json.dumps(build_sidecar(doc, sections, tags_by_section, metrics_by_section, max_tags, max_metrics), indent=2),
        encoding='utf-8',
    )
    return mdx_path, json_path
