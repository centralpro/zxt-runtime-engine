from __future__ import annotations

from pathlib import Path

import yaml

from runtime_blog.models import SiteConfig


def find_content_root(start: Path | None = None) -> Path:
    """Locate content repo root by walking up until site.yml is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "site.yml").is_file():
            return candidate
    raise FileNotFoundError(
        "Cannot find site.yml. Run commands from zxt-runtime-content or pass --root."
    )


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_site_config(root: Path) -> SiteConfig:
    raw = load_yaml(root / "site.yml")
    required = ("title", "description", "url")
    missing = [key for key in required if not raw.get(key)]
    if missing:
        raise ValueError(f"site.yml missing required fields: {', '.join(missing)}")
    return SiteConfig(
        title=str(raw["title"]),
        description=str(raw["description"]),
        url=str(raw["url"]),
        language=str(raw.get("language", "zh-CN")),
        author=str(raw.get("author", "ZXT")),
        timezone=str(raw.get("timezone", "Asia/Hong_Kong")),
        raw=raw,
    )


def package_paths() -> tuple[Path, Path]:
    """Return (templates_dir, static_dir) for the installed/dev package."""
    here = Path(__file__).resolve().parent
    # Development layout: src/runtime_blog + repo templates/static
    repo_root = here.parents[1]
    templates = repo_root / "templates"
    static = repo_root / "static"
    if templates.is_dir() and static.is_dir():
        return templates, static
    # Wheel layout via force-include next to package
    packaged_templates = here / "templates"
    packaged_static = here / "static"
    if packaged_templates.is_dir() and packaged_static.is_dir():
        return packaged_templates, packaged_static
    raise FileNotFoundError("Engine templates/static not found")
