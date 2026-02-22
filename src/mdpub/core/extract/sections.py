"""Token grouping into document sections by heading depth"""


def _heading_level(token) -> int | None:
    """Return heading level (1-6) for heading_open tokens else None."""
    if token.type == 'heading_open' and len(token.tag) == 2 and token.tag[0] == 'h':
        return int(token.tag[1])
    return None


def group_sections(tokens: list, max_nesting: int) -> list[list]:
    """Split tokens into sections; each heading <= max_nesting starts a new one."""
    sections: list[list] = [[]]

    for tok in tokens:
        level = _heading_level(tok)
        if level is not None and level <= max_nesting and sections[-1]:
            sections.append([])
        sections[-1].append(tok)

    return [s for s in sections if s]
