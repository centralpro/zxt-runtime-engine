from __future__ import annotations

import re
from dataclasses import dataclass

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

HEADING_RE = re.compile(
    r'<h([23])(?:\s+[^>]*)?>(.*?)</h\1>',
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
MEDIA_RE = re.compile(r"(@media/[^\s\"')]+)")


@dataclass
class RenderResult:
    html: str
    toc: list[dict[str, str]]
    word_count: int
    reading_minutes: int


def _slugify_heading(text: str) -> str:
    cleaned = TAG_RE.sub("", text).strip().lower()
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", "-", cleaned).strip("-")
    return cleaned or "section"


def _highlight_code(code: str, lang: str, attrs: str) -> str:
    lang = (lang or "").strip()
    try:
        lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
    except ClassNotFound:
        lexer = get_lexer_by_name("text")
    formatter = HtmlFormatter(nowrap=True, cssclass="highlight")
    highlighted = highlight(code, lexer, formatter)
    lang_label = lang or "text"
    filename = ""
    for part in attrs.split():
        if part.startswith("filename="):
            filename = part.split("=", 1)[1].strip("\"'")
    meta = f'<div class="code-meta"><span>{lang_label}</span>'
    if filename:
        meta += f'<span class="code-filename">{filename}</span>'
    meta += (
        '<button type="button" class="copy-btn" data-copy>复制</button></div>'
    )
    return (
        f'<div class="code-block">{meta}'
        f'<pre class="highlight"><code>{highlighted}</code></pre></div>'
    )


def _estimate_reading(text: str) -> tuple[int, int]:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    words = chinese + latin_words
    minutes = max(1, round(words / 400))
    return words, minutes


def resolve_media_refs(markdown: str, media_url_prefix: str = "/media") -> str:
    """Rewrite @media/... to local static paths (OSS deferred)."""

    def repl(match: re.Match[str]) -> str:
        ref = match.group(1)
        relative = ref.removeprefix("@media/")
        return f"{media_url_prefix.rstrip('/')}/{relative}"

    return MEDIA_RE.sub(repl, markdown)


def render_markdown(source: str) -> RenderResult:
    md = (
        MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True})
        .enable("table")
        .enable("strikethrough")
        .use(footnote_plugin)
        .use(tasklists_plugin, enabled=True)
    )

    def fence(renderer, tokens, idx, options, env):  # type: ignore[no-untyped-def]
        token = tokens[idx]
        info = token.info.strip() if token.info else ""
        lang, _, attrs = info.partition(" ")
        return _highlight_code(token.content, lang, attrs)

    md.add_render_rule("fence", fence)

    html = md.render(source)
    toc: list[dict[str, str]] = []
    used_ids: set[str] = set()

    def add_heading(match: re.Match[str]) -> str:
        level = match.group(1)
        inner = match.group(2)
        plain = TAG_RE.sub("", inner).strip()
        base = _slugify_heading(plain)
        slug = base
        n = 2
        while slug in used_ids:
            slug = f"{base}-{n}"
            n += 1
        used_ids.add(slug)
        toc.append({"id": slug, "text": plain, "level": level})
        return f'<h{level} id="{slug}">{inner}</h{level}>'

    html = HEADING_RE.sub(add_heading, html)
    words, minutes = _estimate_reading(source)
    return RenderResult(html=html, toc=toc, word_count=words, reading_minutes=minutes)
