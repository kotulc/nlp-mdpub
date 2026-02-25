"""Convert a ParsedDoc into a flat StagedDoc"""

from mdpub.core.extract.blocks import tokens_to_blocks
from mdpub.core.models import ParsedDoc, StagedDoc


def extract_doc(parsed: ParsedDoc) -> StagedDoc:
    """Convert a ParsedDoc to a flat StagedDoc with no section grouping, hashes, or positions."""
    source_lines = parsed.markdown.splitlines(keepends=True)
    blocks = tokens_to_blocks(parsed.tokens, source_lines)
    return StagedDoc(
        slug=parsed.slug,
        path=str(parsed.path),
        markdown=parsed.markdown,
        frontmatter=parsed.frontmatter,
        content=blocks,
    )
