"""Shared markdown-it token utilities"""


def heading_level(token) -> int | None:
    """Return the heading level (1-6) for a heading_open token, else None."""
    if token.type == 'heading_open' and token.tag and token.tag[0] == 'h' and token.tag[1:].isdigit():
        return int(token.tag[1:])
    return None
