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
    timezone: str = "Asia/Hong_Kong"
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
class SiteData:
    home: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    navigation: dict[str, Any] = field(default_factory=dict)
    social: dict[str, Any] = field(default_factory=dict)
    featured: dict[str, Any] = field(default_factory=dict)
    friends: dict[str, Any] = field(default_factory=dict)
