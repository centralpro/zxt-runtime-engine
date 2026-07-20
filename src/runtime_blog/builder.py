from __future__ import annotations

import json
import shutil
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

from runtime_blog.config import load_site_config, package_paths
from runtime_blog.content_loader import (
    accessible_posts,
    discover_pages,
    discover_photos,
    discover_posts,
    group_photos_by_month,
    load_site_data,
    published_posts,
)
from runtime_blog.markdown_renderer import render_markdown, resolve_media_refs
from runtime_blog.models import Post, SiteConfig
from runtime_blog.page_renderer import PageRenderer
from runtime_blog.validator import LintResult, validate_posts


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy_tree(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def enrich_post(post: Post) -> None:
    body = resolve_media_refs(post.body_md)
    result = render_markdown(body)
    post.html = result.html
    post.toc = result.toc
    post.word_count = result.word_count
    post.reading_minutes = result.reading_minutes


def generate_rss(site: SiteConfig, posts: list[Post]) -> str:
    items = []
    for post in posts[:20]:
        link = f"{site.base_url}{post.url_path}"
        items.append(
            f"""    <item>
      <title>{escape(post.title)}</title>
      <link>{escape(link)}</link>
      <guid>{escape(link)}</guid>
      <pubDate>{post.date.strftime('%a, %d %b %Y 00:00:00 +0800')}</pubDate>
      <description>{escape(post.description)}</description>
    </item>"""
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(site.title)}</title>
    <link>{escape(site.base_url)}/</link>
    <description>{escape(site.description)}</description>
    <language>{escape(site.language)}</language>
{chr(10).join(items)}
  </channel>
</rss>
"""


def generate_sitemap(site: SiteConfig, urls: list[str]) -> str:
    body = "\n".join(
        f"  <url><loc>{escape(site.base_url + u)}</loc></url>" for u in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def generate_robots(site: SiteConfig) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {site.base_url}/sitemap.xml\n"
    )


def generate_llms_txt(site: SiteConfig, posts: list[Post]) -> str:
    lines = [
        f"# {site.title}",
        "",
        site.description,
        "",
        "## Posts",
        "",
    ]
    for post in posts:
        lines.append(f"- [{post.title}]({site.base_url}{post.url_path}): {post.description}")
    lines.append("")
    return "\n".join(lines)


def copy_local_media(root: Path, dist: Path) -> None:
    from runtime_blog.media_assets import copy_media_tree

    public_media = root / "public" / "media"
    if public_media.is_dir():
        copy_media_tree(public_media, dist / "media")
    public_images = root / "public" / "images"
    if public_images.is_dir():
        _copy_tree(public_images, dist / "images")
    favicon = root / "public" / "favicon"
    if favicon.is_dir():
        _copy_tree(favicon, dist / "favicon")


class Builder:
    def __init__(self, root: Path, output: Path | None = None, skip_lint: bool = False):
        self.root = root.resolve()
        self.output = (output or (self.root / "dist")).resolve()
        self.skip_lint = skip_lint
        self.site = load_site_config(self.root)
        self.data = load_site_data(self.root)

    def lint(self) -> LintResult:
        posts = discover_posts(self.root)
        return validate_posts(posts, self.root)

    def build(self) -> Path:
        posts = discover_posts(self.root)
        pages = discover_pages(self.root)

        if not self.skip_lint:
            result = validate_posts(posts, self.root)
            if not result.ok:
                messages = "\n".join(f"[{i.level}] {i.path}: {i.message}" for i in result.errors)
                raise SystemExit(f"Lint failed:\n{messages}")

        for post in posts:
            if post.is_published:
                enrich_post(post)
        for page in pages:
            body = resolve_media_refs(page.body_md)
            rendered = render_markdown(body)
            page.html = rendered.html

        indexed = published_posts(posts)
        reachable = accessible_posts(posts)
        photos = discover_photos(self.root)
        photo_months = group_photos_by_month(photos)

        if self.output.exists():
            shutil.rmtree(self.output)
        self.output.mkdir(parents=True)

        templates_dir, static_dir = package_paths()
        renderer = PageRenderer(self.site, self.data, templates_dir)

        _write(self.output / "index.html", renderer.home(indexed))
        _write(self.output / "posts" / "index.html", renderer.posts_index(indexed))
        _write(self.output / "photos" / "index.html", renderer.photos_index(photos, photo_months))

        for post in reachable:
            _write(
                self.output / "posts" / post.slug / "index.html",
                renderer.article(post, indexed),
            )
            # Markdown source for "view original"
            _write(
                self.output / "posts" / post.slug / "index.md",
                post.source_path.read_text(encoding="utf-8"),
            )

        for page in pages:
            _write(self.output / page.slug / "index.html", renderer.page(page))

        # Categories / tags
        by_category: dict[str, list[Post]] = defaultdict(list)
        by_tag: dict[str, list[Post]] = defaultdict(list)
        for post in indexed:
            by_category[post.category].append(post)
            for tag in post.tags:
                by_tag[tag].append(post)

        for name, group in by_category.items():
            _write(
                self.output / "categories" / name / "index.html",
                renderer.category(name, group),
            )
        for name, group in by_tag.items():
            safe = name.replace("/", "-")
            _write(
                self.output / "tags" / safe / "index.html",
                renderer.tag(name, group),
            )
        _write(self.output / "404.html", renderer.not_found())

        _write(self.output / "rss.xml", generate_rss(self.site, indexed))
        sitemap_urls = (
            ["/"]
            + ["/photos/"]
            + [p.url_path for p in indexed]
            + [f"/{pg.slug}/" for pg in pages]
        )
        _write(self.output / "sitemap.xml", generate_sitemap(self.site, sitemap_urls))
        _write(self.output / "robots.txt", generate_robots(self.site))
        _write(self.output / "llms.txt", generate_llms_txt(self.site, indexed))

        posts_json = [
            {
                "title": p.title,
                "slug": p.slug,
                "description": p.description,
                "date": p.date_iso,
                "category": p.category,
                "tags": p.tags,
                "url": p.url_path,
                "reading_minutes": p.reading_minutes,
            }
            for p in indexed
        ]
        _write(self.output / "posts.json", json.dumps(posts_json, ensure_ascii=False, indent=2))

        search_index = [
            {
                "title": p.title,
                "description": p.description,
                "url": p.url_path,
                "tags": p.tags,
                "category": p.category,
            }
            for p in indexed
        ]
        _write(
            self.output / "search-index.json",
            json.dumps(search_index, ensure_ascii=False, indent=2),
        )

        # Engine static assets
        _copy_tree(static_dir, self.output / "assets")
        # Content public assets
        copy_local_media(self.root, self.output)
        public_root_files = self.root / "public"
        if public_root_files.is_dir():
            for item in public_root_files.iterdir():
                if item.name in {"media", "images", "favicon", "attachments"}:
                    continue
                dest = self.output / item.name
                if item.is_file():
                    shutil.copy2(item, dest)

        return self.output
