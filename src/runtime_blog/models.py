from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass
class SiteConfig:
    title: str
    description: str
    url: str
    language: str = "zh-CN"
    author: str = "ZXT"
    timezone: str = "Asia/Shanghai"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return self.url.rstrip("/")


@dataclass
class Post:
    title: str
    slug: str
    description: str
    date: date
    category: str
    tags: list[str]
    draft: bool
    source_path: Path
    body_md: str
    published_at: datetime | None = None
    updated: date | None = None
    featured: bool = False
    hidden: bool = False
    archived: bool = False
    project: str | None = None
    cover: str | None = None
    html: str = ""
    toc: list[dict[str, str]] = field(default_factory=list)
    reading_minutes: int = 1
    word_count: int = 0

    @property
    def is_published(self) -> bool:
        return not self.draft

    @property
    def in_indexes(self) -> bool:
        return self.is_published and not self.hidden

    @property
    def url_path(self) -> str:
        return f"/posts/{self.slug}/"

    @property
    def date_iso(self) -> str:
        return self.date.isoformat()

    @property
    def updated_iso(self) -> str:
        return (self.updated or self.date).isoformat()

    @property
    def datetime_published(self) -> datetime:
        return datetime.combine(self.date, datetime.min.time())


@dataclass
class Page:
    title: str
    slug: str
    source_path: Path
    body_md: str
    html: str = ""
    description: str = ""


@dataclass
class Photo:
    id: str
    title: str
    image: str
    taken_at: datetime
    location: str = ""
    tags: list[str] = field(default_factory=list)
    caption: str = ""
    source_path: Path | None = None

    @property
    def taken_date(self) -> date:
        return self.taken_at.date()

    @property
    def month_key(self) -> str:
        return self.taken_at.strftime("%Y-%m")

    @property
    def month_label(self) -> str:
        return f"{self.taken_at.year} 年 {self.taken_at.month} 月"

    @property
    def taken_display(self) -> str:
        return self.taken_at.strftime("%Y-%m-%d %H:%M")

    @property
    def taken_iso(self) -> str:
        return self.taken_at.isoformat(sep=" ", timespec="minutes")

    @property
    def web_image(self) -> str:
        from runtime_blog.media_assets import web_image_path

        return web_image_path(self.image)


@dataclass
class SiteData:
    home: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    navigation: dict[str, Any] = field(default_factory=dict)
    social: dict[str, Any] = field(default_factory=dict)
    featured: dict[str, Any] = field(default_factory=dict)
    friends: dict[str, Any] = field(default_factory=dict)
