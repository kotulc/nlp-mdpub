"""Token-to-SectionBlock conversion using source line positions"""

from mdpub.crud.models import SectionBlockEnum
from mdpub.core.models import ExtractedBlock
from mdpub.core.utils.hashing import sha256


BLOCK_TYPE_MAP: dict[str, SectionBlockEnum] = {
    'heading_open':      SectionBlockEnum.heading,
    'bullet_list_open':  SectionBlockEnum.list,
    'ordered_list_open': SectionBlockEnum.list,
    'fence':             SectionBlockEnum.code,
    'code_block':        SectionBlockEnum.code,
    'table_open':        SectionBlockEnum.table,
    'html_block':        SectionBlockEnum.html,
    'blockquote_open':   SectionBlockEnum.quote,
}


def _heading_level(token) -> int | None:
    """Extract heading level (1-6) from a heading_open token tag, else None."""
    if token.tag and token.tag[0] == 'h' and token.tag[1:].isdigit():
        return int(token.tag[1:])
    return None


def _para_type(tokens: list, i: int) -> SectionBlockEnum:
    """Return figure if paragraph at i contains only an image inline, else paragraph."""
    for tok in tokens[i + 1:]:
        if tok.type == 'paragraph_close':
            break
        if tok.type == 'inline' and tok.children:
            non_ws = [c for c in tok.children if c.type not in ('softbreak', 'hardbreak')]
            if len(non_ws) == 1 and non_ws[0].type == 'image':
                return SectionBlockEnum.figure
    return SectionBlockEnum.paragraph


def _source_slice(token, source_lines: list[str]) -> str:
    """Extract raw source for a block via token.map; fallback to token.content."""
    if token.map:
        start, end = token.map
        return ''.join(source_lines[start:end]).rstrip()
    return token.content.rstrip()


def tokens_to_blocks(tokens: list, source_lines: list[str]) -> list[ExtractedBlock]:
    """Convert a section's token list to typed ExtractedBlocks."""
    blocks: list[ExtractedBlock] = []
    position = 0.0
    after_hr = False

    for i, tok in enumerate(tokens):
        if tok.type == 'hr':
            after_hr = True
            continue

        if tok.type == 'paragraph_open':
            block_type = _para_type(tokens, i)
        else:
            block_type = BLOCK_TYPE_MAP.get(tok.type)
            if block_type is None:
                continue

        content = _source_slice(tok, source_lines)
        final_type = SectionBlockEnum.footer if after_hr else block_type
        blocks.append(ExtractedBlock(
            content=content,
            hash=sha256(content),
            type=final_type,
            position=position,
            level=_heading_level(tok),
        ))
        position += 1.0

    return blocks
