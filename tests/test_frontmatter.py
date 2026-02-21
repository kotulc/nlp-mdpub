from mdpub.parser.parse import parse_frontmatter

def test_parse_frontmatter_yaml():
    text = """---
title: Hello
tags:
  - a
  - b
---
# Heading
Body
"""
    parsed = parse_frontmatter(text)
    assert parsed.frontmatter["title"] == "Hello"
    assert parsed.frontmatter["tags"] == ["a", "b"]
    assert "# Heading" in parsed.body
