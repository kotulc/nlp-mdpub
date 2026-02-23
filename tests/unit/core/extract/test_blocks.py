"""Unit tests for core/extract/blocks.py"""

import pytest
from markdown_it import MarkdownIt

from mdpub.core.extract.blocks import tokens_to_blocks
from mdpub.crud.models import SectionBlockEnum


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
    """Fenced code block maps to SectionBlockEnum.code."""
    blocks = _parse_blocks(parser, "```python\nprint('x')\n```\n")
    assert len(blocks) == 1
    assert blocks[0].type == SectionBlockEnum.code


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


@pytest.mark.parametrize("md,expected", [
    ("```python\nprint('x')\n```\n", SectionBlockEnum.code),
    ("    indented code\n",          SectionBlockEnum.code),
    ("> A blockquote.\n",            SectionBlockEnum.quote),
    ("<div>raw html</div>\n",        SectionBlockEnum.html),
])
def test_block_type_mapping(parser, md, expected):
    """Each markdown construct maps to its correct SectionBlockEnum type."""
    blocks = _parse_blocks(parser, md)
    assert any(b.type == expected for b in blocks)


def test_figure_image_only_paragraph(parser):
    """A paragraph containing only an image maps to SectionBlockEnum.figure."""
    blocks = _parse_blocks(parser, "![alt](photo.png)\n")
    assert len(blocks) == 1
    assert blocks[0].type == SectionBlockEnum.figure


def test_paragraph_with_text_and_image(parser):
    """A paragraph mixing text and image stays as SectionBlockEnum.paragraph."""
    blocks = _parse_blocks(parser, "See this: ![alt](photo.png)\n")
    assert any(b.type == SectionBlockEnum.paragraph for b in blocks)
    assert not any(b.type == SectionBlockEnum.figure for b in blocks)
