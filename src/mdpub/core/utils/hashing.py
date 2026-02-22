"""SHA-256 content hashing for document change detection"""

import hashlib


def sha256(content: str) -> str:
    """Return hex-encoded SHA-256 hash of content (64 chars, matches String(64) column)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
