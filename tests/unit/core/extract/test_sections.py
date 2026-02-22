"""Unit tests for core/extract/sections.py"""

import pytest
from markdown_it import MarkdownIt

from mdpub.core.extract.sections import group_sections


@pytest.fixture(name="parser")
def parser_fixture():
    return MarkdownIt("gfm-like", options_update={"linkify": False})


def test_group_sections_by_h1(parser):
    """Each h1 heading starts a new section."""
    tokens = parser.parse("# A\n\npara\n\n# B\n\npara\n")
    sections = group_sections(tokens, max_nesting=1)
    assert len(sections) == 2


def test_group_sections_no_headings(parser):
    """Content with no headings produces a single section."""
    tokens = parser.parse("Just a paragraph.\n")
    sections = group_sections(tokens, max_nesting=6)
    assert len(sections) == 1


def test_group_sections_max_nesting(parser):
    """Headings deeper than max_nesting do not start a new section."""
    tokens = parser.parse("## Section\n\n### Deep\n\nContent.\n")
    sections = group_sections(tokens, max_nesting=2)
    assert len(sections) == 1

    sections = group_sections(tokens, max_nesting=3)
    assert len(sections) == 2


def test_deep_heading_stays_in_section(parser):
    """h3 with max_nesting=2 stays as a block in the current section."""
    tokens = parser.parse("## Top\n\n### Sub\n\nBody.\n")
    sections = group_sections(tokens, max_nesting=2)
    assert len(sections) == 1
    types = [t.type for t in sections[0]]
    assert 'heading_open' in types  # h3 is present as a block token


def test_group_sections_preamble(parser):
    """Content before the first heading forms a leading section."""
    tokens = parser.parse("Intro text.\n\n# Section\n\nBody.\n")
    sections = group_sections(tokens, max_nesting=1)
    assert len(sections) == 2
    # First section has no heading_open
    assert not any(t.type == 'heading_open' for t in sections[0])
