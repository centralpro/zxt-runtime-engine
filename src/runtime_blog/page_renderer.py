from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from runtime_blog.config import package_paths
from runtime_blog.models import Page, Post, SiteConfig, SiteData


def create_env(templates_dir: Path | None = None) -> Environment:
    if templates_dir is None:
        templates_dir, _ = package_paths()
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


class PageRenderer:
    def __init__(self, site: SiteConfig, data: SiteData, templates_dir: Path | None = None):
        self.site = site
        self.data = data
        self.env = create_env(templates_dir)

    def _base_ctx(self) -> dict:
        nav = self.data.navigation.get("items") or [
            {"label": "首页", "href": "/"},
            {"label": "文章", "href": "/posts/"},
            {"label": "关于", "href": "/about/"},
        ]
        return {
            "site": self.site,
            "data": self.data,
            "nav": nav,
            "profile": self.data.profile,
            "social": self.data.social,
        }

    def render(self, template_name: str, **ctx) -> str:
        template = self.env.get_template(template_name)
        return template.render(**self._base_ctx(), **ctx)

    def home(self, posts: list[Post]) -> str:
        featured_slugs = self.data.featured.get("slugs") or []
        featured = [p for p in posts if p.slug in featured_slugs or p.featured][:5]
        latest = posts[:6]
        return self.render(
            "home.html",
            home=self.data.home,
            latest_posts=latest,
            featured_posts=featured,
        )

    def posts_index(self, posts: list[Post]) -> str:
        return self.render("posts.html", posts=posts, page_title="文章")

    def article(self, post: Post, posts: list[Post]) -> str:
        indexed = [p for p in posts if p.in_indexes]
        idx = next((i for i, p in enumerate(indexed) if p.slug == post.slug), None)
        prev_post = indexed[idx + 1] if idx is not None and idx + 1 < len(indexed) else None
        next_post = indexed[idx - 1] if idx is not None and idx > 0 else None
        related = [
            p
            for p in indexed
            if p.slug != post.slug
            and (p.category == post.category or set(p.tags) & set(post.tags))
        ][:3]
        return self.render(
            "article.html",
            post=post,
            prev_post=prev_post,
            next_post=next_post,
            related_posts=related,
        )

    def page(self, page: Page) -> str:
        template = "about.html" if page.slug == "about" else "page.html"
        # fall back if dedicated template missing
        try:
            self.env.get_template(template)
        except Exception:
            template = "page.html"
        return self.render(template, page=page)

    def not_found(self) -> str:
        return self.render("404.html")

    def category(self, name: str, posts: list[Post]) -> str:
        return self.render(
            "category.html",
            category=name,
            posts=posts,
            page_title=f"分类 · {name}",
        )

    def tag(self, name: str, posts: list[Post]) -> str:
        return self.render(
            "tag.html",
            tag=name,
            posts=posts,
            page_title=f"标签 · {name}",
        )

    def archive(self, years: dict[int, list[Post]]) -> str:
        return self.render("archive.html", years=years, page_title="归档")
