from __future__ import annotations

import re
from datetime import date, datetime, time
from pathlib import Path

import yaml

from runtime_blog.config import load_yaml
from runtime_blog.media_assets import is_heif, read_taken_at, resolve_media_file
from runtime_blog.models import Page, Photo, Post, SiteData

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


def _parse_published_at(value: object, fallback: date) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        text = value.strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    raise ValueError(f"Invalid published_at/date time: {value!r}")


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
    post_date = (
        _parse_date(meta.get("date", date.today()), "date")
        if meta.get("date") is not None
        else date.today()
    )
    published_raw = meta.get("published_at") or meta.get("date")
    return Post(
        title=_as_str(meta.get("title")),
        slug=_as_str(meta.get("slug")),
        description=_as_str(meta.get("description")),
        date=post_date,
        published_at=_parse_published_at(published_raw, post_date),
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


def _parse_taken_at(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        text = value.strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    raise ValueError(f"Invalid taken_at: {value!r}")


def load_photo(path: Path) -> Photo:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: photo YAML must be a mapping")
    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        raise ValueError(f"{path}: tags must be a list")
    photo_id = _as_str(raw.get("id") or path.stem)
    image = _as_str(raw.get("image"))
    if not image:
        raise ValueError(f"{path}: image is required")
    if not image.startswith("/"):
        image = "/" + image.lstrip("/")
    return Photo(
        id=photo_id,
        title=_as_str(raw.get("title") or photo_id),
        image=image,
        taken_at=_parse_taken_at(raw.get("taken_at")),
        location=_as_str(raw.get("location")),
        tags=[str(t) for t in tags],
        caption=_as_str(raw.get("caption")),
        source_path=path,
    )


def discover_photos(root: Path) -> list[Photo]:
    photos_dir = root / "content" / "photos"
    photos: list[Photo] = []
    if photos_dir.is_dir():
        photos = [load_photo(path) for path in sorted(photos_dir.glob("*.yml"))]
        photos.extend(load_photo(path) for path in sorted(photos_dir.glob("*.yaml")))
    by_id: dict[str, Photo] = {}
    covered_media: set[str] = set()
    for photo in photos:
        by_id[photo.id] = photo
        media = resolve_media_file(root, photo.image)
        if media:
            covered_media.add(media.name.lower())
        covered_media.add(Path(photo.image).name.lower())
        covered_media.add(Path(photo.web_image).name.lower())

    media_dir = root / "public" / "media" / "photos"
    if media_dir.is_dir():
        for path in sorted(media_dir.iterdir()):
            if not path.is_file() or not is_heif(path):
                continue
            if path.name.lower() in covered_media:
                continue
            taken = read_taken_at(path) or datetime.fromtimestamp(path.stat().st_mtime)
            photo_id = path.stem.lower().replace("_", "-")
            image = f"/media/photos/{path.name}"
            by_id[photo_id] = Photo(
                id=photo_id,
                title=photo_id,
                image=image,
                taken_at=taken,
            )
            covered_media.add(path.name.lower())

    return sorted(by_id.values(), key=lambda p: (p.taken_at, p.id), reverse=True)


def group_photos_by_month(photos: list[Photo]) -> list[dict]:
    groups: dict[str, dict] = {}
    order: list[str] = []
    for photo in photos:
        key = photo.month_key
        if key not in groups:
            groups[key] = {"key": key, "label": photo.month_label, "photos": []}
            order.append(key)
        groups[key]["photos"].append(photo)
    return [groups[k] for k in order]


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


def _post_sort_key(post: Post) -> tuple[float, str]:
    """Newest first by published_at; slug ascending breaks ties."""
    when = post.published_at or datetime.combine(post.date, time.min)
    return (-when.timestamp(), post.slug)


def published_posts(posts: list[Post]) -> list[Post]:
    return sorted(
        [p for p in posts if p.in_indexes],
        key=_post_sort_key,
    )


def accessible_posts(posts: list[Post]) -> list[Post]:
    """Published posts including hidden (reachable by URL, not listed)."""
    return [p for p in posts if p.is_published]
