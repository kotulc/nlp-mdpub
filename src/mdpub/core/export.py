"""Export pipeline: build MDX/MD content and write output files"""

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


def build_mdx(
    doc: Document,
    body: str,
    tags: dict[str, float] | None = None,
    metrics: dict[str, float] | None = None,
    ) -> str:
    """Return body with a merged YAML frontmatter block prepended (slug + user fields + tags/metrics)."""
    fm = dict(doc.frontmatter or {})
    fm['slug'] = doc.slug
    if tags:
        fm['tags'] = tags
    if metrics:
        fm['metrics'] = metrics
    header = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{header}---\n\n{body.lstrip()}"


def write_doc(
    doc: Document,
    session: Session,
    output_dir: Path,
    fmt: str = 'mdx',
    max_tags: int = 0,
    max_metrics: int = 0,
    ) -> Path:
    """Write MDX/MD for a single document with aggregated tags/metrics in frontmatter.

    Tags and metrics are merged across all non-hidden sections (last-wins on duplicate keys).
    max_tags / max_metrics truncate the output (0 = unlimited).
    Output path mirrors the source directory structure:
      output_dir / Path(doc.path).parent / doc.slug.{fmt}

    Returns mdx_path.
    """
    src = Path(doc.path)
    dest_dir = output_dir / src.parent
    dest_dir.mkdir(parents=True, exist_ok=True)

    sections = session.exec(select(Section).where(Section.document_id == doc.id)).all()
    blocks_by_section = {
        s.id: session.exec(select(SectionBlock).where(SectionBlock.section_id == s.id)).all()
        for s in sections
    }

    # Aggregate tags/metrics across non-hidden sections in position order.
    tags: dict[str, float] = {}
    metrics: dict[str, float] = {}
    for s in sorted(sections, key=lambda s: s.position):
        if s.hidden:
            continue
        for st in sorted(
            session.exec(select(SectionTag).where(SectionTag.section_id == s.id)).all(),
            key=lambda t: t.position or 0,
        ):
            tags[st.tag_name] = st.relevance
        for m in session.exec(select(SectionMetric).where(SectionMetric.section_id == s.id)).all():
            metrics[m.name] = m.value

    if max_tags:
        tags = dict(list(tags.items())[:max_tags])
    if max_metrics:
        metrics = dict(list(metrics.items())[:max_metrics])

    body = build_body(sections, blocks_by_section)
    mdx_path = dest_dir / f"{doc.slug}.{fmt}"
    mdx_path.write_text(build_mdx(doc, body, tags or None, metrics or None), encoding='utf-8')
    return mdx_path
