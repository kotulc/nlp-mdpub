"""Shared fixtures for core unit tests"""

import pytest
from markdown_it import MarkdownIt


SAMPLE_MD = """\
# Heading 1

A paragraph with **bold** text.

## Heading 2

- item one
- item two

```python
print("hello")
```

---

Footer paragraph.
"""

SAMPLE_FM_MD = """\
---
title: Test Doc
slug: test-doc
tags: [a, b]
---

# Title

Body content.
"""


@pytest.fixture(name="parser")
def parser_fixture():
    return MarkdownIt("gfm-like", options_update={"linkify": False})


@pytest.fixture(name="sample_tokens")
def sample_tokens_fixture(parser):
    return parser.parse(SAMPLE_MD)


@pytest.fixture(name="sample_lines")
def sample_lines_fixture():
    return SAMPLE_MD.splitlines(keepends=True)
