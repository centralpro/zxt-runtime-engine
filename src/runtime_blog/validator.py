from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from runtime_blog.models import Post

REQUIRED_FIELDS = ("title", "slug", "description", "date", "category", "tags", "draft")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INTERNAL_LINK_RE = re.compile(r"\]\((/[^)\s]+)\)")
MEDIA_RE = re.compile(r"@media/([^\s\"')]+)")
HEADING_LINE_RE = re.compile(r"^(#{1,6})\s+", re.MULTILINE)


@dataclass
class LintIssue:
    level: str  # error | warning
    path: str
    message: str


@dataclass
class LintResult:
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, level: str, path: Path | str, message: str) -> None:
        self.issues.append(LintIssue(level=level, path=str(path), message=message))


def validate_posts(posts: list[Post], root: Path) -> LintResult:
    result = LintResult()
    seen_slugs: dict[str, Path] = {}

    for post in posts:
        rel = post.source_path.relative_to(root) if post.source_path.is_relative_to(root) else post.source_path

        if not post.title:
            result.add("error", rel, "missing required field: title")
        if not post.slug:
            result.add("error", rel, "missing required field: slug")
        elif not SLUG_RE.match(post.slug):
            result.add("error", rel, f"invalid slug format: {post.slug}")
        if not post.description:
            result.add("error", rel, "missing required field: description")
        if not post.category:
            result.add("error", rel, "missing required field: category")
        if not isinstance(post.tags, list) or not post.tags:
            result.add("error", rel, "tags must be a non-empty list")
        else:
            for tag in post.tags:
                if not str(tag).strip():
                    result.add("error", rel, "empty tag not allowed")

        if post.slug:
            if post.slug in seen_slugs:
                result.add(
                    "error",
                    rel,
                    f"duplicate slug '{post.slug}' also used by {seen_slugs[post.slug]}",
                )
            else:
                seen_slugs[post.slug] = Path(str(rel))

        # Draft under published year folder is fine; warn if published under drafts/
        if not post.draft and "drafts" in post.source_path.parts:
            result.add(
                "error",
                rel,
                "published post (draft: false) must not live under drafts/",
            )

        # Media existence
        for media_ref in MEDIA_RE.findall(post.body_md):
            media_path = root / "public" / "media" / media_ref
            if not media_path.is_file():
                # also allow public/images style via @media pointing into public/media
                alt = root / "public" / media_ref
                if not alt.is_file():
                    result.add("error", rel, f"missing media file: @media/{media_ref}")

        # Image alt checks for markdown images
        for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", post.body_md):
            alt, _url = match.group(1), match.group(2)
            if not alt.strip():
                result.add("warning", rel, "image missing alt text")

        # Heading hierarchy: jump more than one level
        levels = [len(m.group(1)) for m in HEADING_LINE_RE.finditer(post.body_md)]
        prev = 0
        for level in levels:
            if prev and level > prev + 1:
                result.add(
                    "warning",
                    rel,
                    f"heading hierarchy jumps from h{prev} to h{level}",
                )
            prev = level

        # Internal links to other posts — soft check after all slugs known later
        _ = INTERNAL_LINK_RE  # reserved for future cross-link pass

    # Second pass: internal /posts/<slug>/ links
    known = {p.slug for p in posts if p.is_published}
    for post in posts:
        rel = post.source_path.relative_to(root) if post.source_path.is_relative_to(root) else post.source_path
        for link in INTERNAL_LINK_RE.findall(post.body_md):
            if link.startswith("/posts/"):
                parts = [p for p in link.strip("/").split("/") if p]
                if len(parts) >= 2:
                    target = parts[1]
                    if target not in known and target != post.slug:
                        # might be draft — still warn
                        all_slugs = {p.slug for p in posts}
                        if target not in all_slugs:
                            result.add("error", rel, f"broken internal link: {link}")

    return result
