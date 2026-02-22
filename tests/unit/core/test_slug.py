"""Unit tests for core/utils/slug.py"""

import pytest

from mdpub.core.utils.slug import slugify


@pytest.mark.parametrize("text,expected", [
    ("Hello World", "hello-world"),
    ("my_file_name", "my-file-name"),
    ("  leading and trailing  ", "leading-and-trailing"),
    ("multiple---hyphens", "multiple-hyphens"),
    ("Special! Ch@rs#", "special-chrs"),
    ("", ""),
])
def test_slugify_basic(text, expected):
    """slugify converts text to lowercase hyphenated slug."""
    assert slugify(text) == expected


def test_slugify_preserves_hyphens():
    """slugify keeps existing hyphens intact."""
    assert slugify("already-slugified") == "already-slugified"


def test_slugify_strips_leading_trailing_hyphens():
    """slugify strips leading/trailing hyphens from result."""
    assert not slugify("!leading").startswith("-")
