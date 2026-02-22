"""Pure utility for generating unified diffs between two text strings"""

import difflib


def diff_summary(old: str, new: str) -> dict[str, int]:
    """Return added/deleted/unchanged line counts. Useful for compact change stats."""
    old_lines, new_lines = old.splitlines(), new.splitlines()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    added = deleted = unchanged = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            unchanged += i2 - i1
        elif tag == "replace":
            deleted += i2 - i1
            added += j2 - j1
        elif tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            deleted += i2 - i1

    return {"added": added, "deleted": deleted, "unchanged": unchanged}


def unified_diff(
    old: str,
    new: str,
    from_label: str = "version_a",
    to_label: str = "version_b",
    context: int = 3,
    ) -> list[str]:
    """Return unified diff lines comparing old to new. Empty list if identical.

    Returns a list of lines; join with '' for display (lines already include newlines).
    Pass meaningful labels (e.g. 'v3', 'current') for a readable diff header.
    """
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return list(
        difflib.unified_diff(old_lines, new_lines, fromfile=from_label, tofile=to_label, n=context)
    )
