from __future__ import annotations

from pathlib import Path

from runtime_blog.builder import Builder
from runtime_blog.config import load_site_config
from runtime_blog.content_loader import load_post, parse_front_matter
from runtime_blog.markdown_renderer import render_markdown, resolve_media_refs
from runtime_blog.validator import validate_posts


def _write_minimal_content(root: Path) -> None:
    (root / "content" / "posts" / "2026").mkdir(parents=True)
    (root / "content" / "posts" / "drafts").mkdir(parents=True)
    (root / "content" / "pages").mkdir(parents=True)
    (root / "content" / "data").mkdir(parents=True)
    (root / "public" / "media" / "posts" / "demo").mkdir(parents=True)

    (root / "site.yml").write_text(
        """
title: ZXT / Runtime
description: Test site
url: http://127.0.0.1:8000
author: ZXT
language: zh-CN
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "content" / "data" / "home.yml").write_text(
        "status: Runtime online\ntagline: Test tagline\nintro: Hello\n",
        encoding="utf-8",
    )
    (root / "content" / "data" / "navigation.yml").write_text(
        "items:\n  - label: 首页\n    href: /\n  - label: 文章\n    href: /posts/\n",
        encoding="utf-8",
    )
    (root / "content" / "data" / "profile.yml").write_text("name: ZXT\n", encoding="utf-8")
    (root / "content" / "data" / "featured.yml").write_text("slugs: []\n", encoding="utf-8")
    (root / "content" / "data" / "social.yml").write_text("{}\n", encoding="utf-8")
    (root / "content" / "data" / "friends.yml").write_text("{}\n", encoding="utf-8")

    (root / "public" / "media" / "posts" / "demo" / "cover.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    )

    (root / "content" / "posts" / "2026" / "hello.md").write_text(
        """---
title: Hello Runtime
slug: hello-runtime
description: First published post
date: 2026-07-20
category: Engineering
tags:
  - python
  - uv
draft: false
featured: true
---

## 开篇

这是一篇测试文章，包含 `inline` 代码。

```python
print("hello")
```

![封面](@media/posts/demo/cover.png)

### 小节标题

继续阅读。
""",
        encoding="utf-8",
    )

    (root / "content" / "posts" / "drafts" / "wip.md").write_text(
        """---
title: WIP Draft
slug: wip-draft
description: Should not publish
date: 2026-07-19
category: Engineering
tags:
  - draft
draft: true
---

草稿内容。
""",
        encoding="utf-8",
    )

    (root / "content" / "pages" / "about.md").write_text(
        """---
title: 关于
slug: about
description: About page
---

我是 ZXT。
""",
        encoding="utf-8",
    )


def test_parse_front_matter():
    meta, body = parse_front_matter("---\ntitle: A\n---\n\nBody\n")
    assert meta["title"] == "A"
    assert body.startswith("Body")


def test_render_markdown_code_and_toc():
    result = render_markdown("## Hello\n\n```python\nprint(1)\n```\n")
    assert 'id="hello"' in result.html
    assert "code-block" in result.html
    assert result.toc[0]["text"] == "Hello"
    assert result.reading_minutes >= 1


def test_resolve_media_refs():
    assert resolve_media_refs("![](@media/posts/a.png)") == "![](/media/posts/a.png)"


def test_load_site_and_build(tmp_path: Path):
    _write_minimal_content(tmp_path)
    site = load_site_config(tmp_path)
    assert site.title == "ZXT / Runtime"

    out = Builder(tmp_path).build()
    assert (out / "index.html").is_file()
    assert (out / "posts" / "hello-runtime" / "index.html").is_file()
    assert (out / "posts" / "wip-draft").exists() is False
    assert (out / "about" / "index.html").is_file()
    assert (out / "rss.xml").is_file()
    assert (out / "sitemap.xml").is_file()
    assert (out / "robots.txt").is_file()
    assert (out / "llms.txt").is_file()
    assert (out / "posts.json").is_file()
    assert (out / "media" / "posts" / "demo" / "cover.png").is_file()
    assert (out / "assets" / "css" / "runtime.css").is_file()

    home = (out / "index.html").read_text(encoding="utf-8")
    assert "Hello Runtime" in home
    assert "WIP Draft" not in home

    posts_json = (out / "posts.json").read_text(encoding="utf-8")
    assert "hello-runtime" in posts_json
    assert "wip-draft" not in posts_json


def test_lint_duplicate_slug(tmp_path: Path):
    _write_minimal_content(tmp_path)
    (tmp_path / "content" / "posts" / "2026" / "dup.md").write_text(
        """---
title: Dup
slug: hello-runtime
description: dup
date: 2026-07-21
category: Engineering
tags:
  - x
draft: false
---

dup
""",
        encoding="utf-8",
    )
    posts = []
    from runtime_blog.content_loader import discover_posts

    posts = discover_posts(tmp_path)
    result = validate_posts(posts, tmp_path)
    assert not result.ok
    assert any("duplicate slug" in i.message for i in result.errors)


def test_lint_missing_required(tmp_path: Path):
    _write_minimal_content(tmp_path)
    bad = tmp_path / "content" / "posts" / "2026" / "bad.md"
    bad.write_text(
        """---
title: Bad
slug: bad-post
description: 
date: 2026-07-21
category: 
tags: []
draft: false
---

x
""",
        encoding="utf-8",
    )
    from runtime_blog.content_loader import discover_posts

    result = validate_posts(discover_posts(tmp_path), tmp_path)
    assert not result.ok


def test_load_post_draft_flag(tmp_path: Path):
    _write_minimal_content(tmp_path)
    post = load_post(tmp_path / "content" / "posts" / "drafts" / "wip.md")
    assert post.draft is True
    assert post.in_indexes is False
