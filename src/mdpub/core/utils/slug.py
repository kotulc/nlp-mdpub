"""Slug generation for document identifiers"""

import re


def slugify(text: str) -> str:
    """Convert text to a lowercase, hyphen-separated URL-safe slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return re.sub(r'-+', '-', text).strip('-')
