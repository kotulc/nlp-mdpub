"""Convert a ParsedDoc into a structured ExtractedDoc"""

from mdpub.core.extract.blocks import tokens_to_blocks
from mdpub.core.extract.sections import group_sections
from mdpub.core.models import ExtractedDoc, ExtractedSection, ParsedDoc
from mdpub.core.utils.hashing import sha256


def extract_doc(parsed: ParsedDoc, max_nesting: int = 6) -> ExtractedDoc:
    """Convert a ParsedDoc into sections and typed blocks."""
    source_lines = parsed.markdown.splitlines(keepends=True)
    sections = []

    for position, group in enumerate(group_sections(parsed.tokens, max_nesting)):
        blocks = tokens_to_blocks(group, source_lines)
        sections.append(ExtractedSection(
            hash=sha256(''.join(b.content for b in blocks)),
            position=position,
            blocks=blocks,
        ))

    return ExtractedDoc(
        slug=parsed.slug,
        path=str(parsed.path),
        raw_markdown=parsed.raw_markdown,
        markdown=parsed.markdown,
        hash=parsed.hash,
        frontmatter=parsed.frontmatter,
        sections=sections,
    )
