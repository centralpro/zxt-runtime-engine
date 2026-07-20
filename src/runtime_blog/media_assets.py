from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

HEIF_SUFFIXES = {".heif", ".heic"}


def is_heif(path: Path) -> bool:
    return path.suffix.lower() in HEIF_SUFFIXES


def web_image_path(image_url: str) -> str:
    """Browser-served path: HEIF/HEIC sources become .jpg in dist."""
    path = Path(image_url)
    if path.suffix.lower() in HEIF_SUFFIXES:
        return str(path.with_suffix(".jpg"))
    return image_url


def resolve_media_file(root: Path, image_url: str) -> Path | None:
    """Resolve /media/... to a file under public/, including HEIF fallbacks."""
    rel = image_url.lstrip("/")
    if not rel.startswith("media/"):
        return None
    full = root / "public" / rel
    if full.is_file():
        return full
    stem = full.with_suffix("")
    for ext in (".heif", ".heic", ".HEIF", ".HEIC"):
        alt = stem.with_suffix(ext)
        if alt.is_file():
            return alt
    return None


def _convert_with_pillow(src: Path, dest: Path) -> None:
    from PIL import Image

    import pillow_heif

    pillow_heif.register_heif_opener()
    with Image.open(src) as img:
        rgb = img.convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(dest, format="JPEG", quality=90, optimize=True)


def _convert_with_sips(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["sips", "-s", "format", "jpeg", str(src), "--out", str(dest)],
        check=True,
        capture_output=True,
    )


def convert_heif_to_jpg(src: Path, dest: Path) -> None:
    """Convert HEIF/HEIC to JPEG for web delivery."""
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        return
    try:
        _convert_with_pillow(src, dest)
        return
    except Exception:
        pass
    try:
        _convert_with_sips(src, dest)
        return
    except Exception as exc:
        raise RuntimeError(
            f"Failed to convert HEIF to JPG: {src.name}. "
            "Install pillow-heif (recommended) or use macOS sips."
        ) from exc


def read_taken_at(path: Path) -> datetime | None:
    """Read DateTimeOriginal from JPEG or HEIF, if available."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        import pillow_heif

        if is_heif(path):
            pillow_heif.register_heif_opener()
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            for tag_id, val in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag in ("DateTimeOriginal", "DateTime"):
                    date_part, time_part = str(val).strip().split(" ", 1)
                    date_part = date_part.replace(":", "-")
                    hh, mm, *_ = time_part.split(":")
                    return datetime.strptime(f"{date_part} {hh}:{mm}", "%Y-%m-%d %H:%M")
    except Exception:
        return None
    return None


def copy_media_tree(src: Path, dest: Path) -> None:
    """Copy public/media into dist; HEIF/HEIC are converted to JPG, not shipped as-is."""
    if not src.is_dir():
        return
    if dest.exists():
        shutil.rmtree(dest)
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        target = dest / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if is_heif(item):
            convert_heif_to_jpg(item, target.with_suffix(".jpg"))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
