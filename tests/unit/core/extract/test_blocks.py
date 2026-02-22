"""Unit tests for core/extract/blocks.py"""

import pytest
from markdown_it import MarkdownIt

from mdpub.core.extract.blocks import tokens_to_blocks
from mdpub.crud.tables import SectionBlockEnum


@pytest.fixture(name="parser")
def parser_fixture():
    return MarkdownIt("gfm-like", options_update={"linkify": False})


def _parse_blocks(parser, md: str):
    tokens = parser.parse(md)
    lines = md.splitlines(keepends=True)
    return tokens_to_blocks(tokens, lines)


def test_heading_block(parser):
    """heading_open token maps to SectionBlockEnum.heading with correct level."""
    blocks = _parse_blocks(parser, "## Hello\n")
    assert len(blocks) == 1
    assert blocks[0].type == SectionBlockEnum.heading
    assert blocks[0].level == 2


def test_paragraph_block(parser):
    """paragraph_open token maps to SectionBlockEnum.paragraph."""
    blocks = _parse_blocks(parser, "A paragraph.\n")
    assert any(b.type == SectionBlockEnum.paragraph for b in blocks)


def test_list_block(parser):
    """bullet_list_open maps to SectionBlockEnum.list."""
    blocks = _parse_blocks(parser, "- item one\n- item two\n")
    assert any(b.type == SectionBlockEnum.list for b in blocks)


def test_fence_block(parser):
    """Fenced code block maps to SectionBlockEnum.content."""
    blocks = _parse_blocks(parser, "```python\nprint('x')\n```\n")
    assert len(blocks) == 1
    assert blocks[0].type == SectionBlockEnum.content


def test_footer_after_hr(parser):
    """Blocks after an hr token are typed as SectionBlockEnum.footer."""
    blocks = _parse_blocks(parser, "Para.\n\n---\n\nFooter text.\n")
    footer_blocks = [b for b in blocks if b.type == SectionBlockEnum.footer]
    assert len(footer_blocks) == 1


def test_source_slice_uses_map(parser):
    """Block content matches the original source lines via token.map."""
    md = "## My Heading\n\nSome paragraph.\n"
    blocks = _parse_blocks(parser, md)
    heading = next(b for b in blocks if b.type == SectionBlockEnum.heading)
    assert "## My Heading" in heading.content


def test_block_positions_increment(parser):
    """Block positions increment monotonically within a section."""
    blocks = _parse_blocks(parser, "# H\n\nPara.\n\n- list\n")
    positions = [b.position for b in blocks]
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)
