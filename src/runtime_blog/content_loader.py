from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import yaml

from runtime_blog.config import load_yaml
from runtime_blog.models import Page, Post, SiteData

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_front_matter(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError("Front matter must be a YAML mapping")
    return meta, match.group(2).lstrip("\n")


def _parse_date(value: object, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Invalid date for {field_name}: {value!r}")


def _as_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def load_post(path: Path) -> Post:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    tags = meta.get("tags") or []
    if not isinstance(tags, list):
        raise ValueError(f"{path}: tags must be a list")
    return Post(
        title=_as_str(meta.get("title")),
        slug=_as_str(meta.get("slug")),
        description=_as_str(meta.get("description")),
        date=_parse_date(meta.get("date", date.today()), "date")
        if meta.get("date") is not None
        else date.today(),
        updated=_parse_date(meta["updated"], "updated") if meta.get("updated") else None,
        category=_as_str(meta.get("category")),
        tags=[str(t) for t in tags],
        draft=bool(meta.get("draft", True)),
        featured=bool(meta.get("featured", False)),
        hidden=bool(meta.get("hidden", False)),
        archived=bool(meta.get("archived", False)),
        project=_as_str(meta["project"]) if meta.get("project") else None,
        cover=_as_str(meta["cover"]) if meta.get("cover") else None,
        source_path=path,
        body_md=body,
    )


def load_page(path: Path) -> Page:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    slug = str(meta.get("slug") or path.stem)
    return Page(
        title=str(meta.get("title", slug.title())),
        slug=slug,
        description=str(meta.get("description", "")),
        source_path=path,
        body_md=body,
    )


def discover_posts(root: Path) -> list[Post]:
    posts_dir = root / "content" / "posts"
    if not posts_dir.is_dir():
        return []
    posts: list[Post] = []
    for path in sorted(posts_dir.rglob("*.md")):
        posts.append(load_post(path))
    return posts


def discover_pages(root: Path) -> list[Page]:
    pages_dir = root / "content" / "pages"
    if not pages_dir.is_dir():
        return []
    return [load_page(path) for path in sorted(pages_dir.glob("*.md"))]


def load_site_data(root: Path) -> SiteData:
    data_dir = root / "content" / "data"
    return SiteData(
        home=load_yaml(data_dir / "home.yml"),
        profile=load_yaml(data_dir / "profile.yml"),
        navigation=load_yaml(data_dir / "navigation.yml"),
        social=load_yaml(data_dir / "social.yml"),
        featured=load_yaml(data_dir / "featured.yml"),
        friends=load_yaml(data_dir / "friends.yml"),
    )


def published_posts(posts: list[Post]) -> list[Post]:
    return sorted(
        [p for p in posts if p.in_indexes],
        key=lambda p: (p.date, p.slug),
        reverse=True,
    )


def accessible_posts(posts: list[Post]) -> list[Post]:
    """Published posts including hidden (reachable by URL, not listed)."""
    return [p for p in posts if p.is_published]
