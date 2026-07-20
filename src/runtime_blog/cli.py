from __future__ import annotations

import http.server
import socketserver
import threading
import time
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from slugify import slugify
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from runtime_blog.builder import Builder
from runtime_blog.config import find_content_root

app = typer.Typer(
    name="runtime-blog",
    help="ZXT / Runtime static blog CLI",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _root_option() -> Path:
    return find_content_root()


@app.command()
def build(
    root: Optional[Path] = typer.Option(None, "--root", help="Content repo root"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    skip_lint: bool = typer.Option(False, "--skip-lint", help="Skip content validation"),
) -> None:
    """Build the static site into dist/."""
    content_root = (root or find_content_root()).resolve()
    builder = Builder(content_root, output=output, skip_lint=skip_lint)
    dest = builder.build()
    console.print(f"[green]Built[/green] → {dest}")


@app.command()
def lint(
    root: Optional[Path] = typer.Option(None, "--root", help="Content repo root"),
) -> None:
    """Validate content front matter and references."""
    content_root = (root or find_content_root()).resolve()
    result = Builder(content_root).lint()
    for issue in result.issues:
        color = "red" if issue.level == "error" else "yellow"
        console.print(f"[{color}]{issue.level}[/{color}] {issue.path}: {issue.message}")
    if not result.ok:
        console.print(f"[red]Lint failed with {len(result.errors)} error(s)[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Lint passed[/green]")


@app.command("new")
def new_post(
    title: str = typer.Argument(..., help="Post title"),
    root: Optional[Path] = typer.Option(None, "--root", help="Content repo root"),
) -> None:
    """Create a new draft Markdown post."""
    content_root = (root or find_content_root()).resolve()
    slug = slugify(title, allow_unicode=False) or "untitled"
    today = date.today()
    drafts = content_root / "content" / "posts" / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    path = drafts / f"{today.isoformat()}-{slug}.md"
    if path.exists():
        console.print(f"[red]File already exists:[/red] {path}")
        raise typer.Exit(code=1)
    body = f"""---
title: {title}
slug: {slug}
description: TODO — 补充摘要
date: {today.isoformat()}
category: Engineering
tags:
  - draft
draft: true
featured: false
hidden: false
archived: false
---

# {title}

在这里开始写作。
"""
    path.write_text(body, encoding="utf-8")
    console.print(f"[green]Created[/green] {path}")


class _RebuildHandler(FileSystemEventHandler):
    def __init__(self, root: Path, rebuild_flag: list[bool]) -> None:
        super().__init__()
        self.root = root
        self.rebuild_flag = rebuild_flag
        self._last = 0.0

    def on_any_event(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if "dist" in path.parts or path.name.startswith("."):
            return
        now = time.time()
        if now - self._last < 0.4:
            return
        self._last = now
        self.rebuild_flag[0] = True


@app.command()
def dev(
    root: Optional[Path] = typer.Option(None, "--root", help="Content repo root"),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Build once, serve dist/, and rebuild on content changes."""
    content_root = (root or find_content_root()).resolve()
    builder = Builder(content_root, skip_lint=False)
    try:
        dest = builder.build()
    except SystemExit as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Serving[/green] http://{host}:{port}/  (from {dest})")

    rebuild_flag = [False]
    handler = _RebuildHandler(content_root, rebuild_flag)
    observer = Observer()
    observer.schedule(handler, str(content_root / "content"), recursive=True)
    observer.schedule(handler, str(content_root / "public"), recursive=True)
    if (content_root / "site.yml").exists():
        observer.schedule(handler, str(content_root), recursive=False)
    observer.start()

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            super().__init__(*args, directory=str(dest), **kwargs)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            console.print(f"[dim]{self.address_string()} - {format % args}[/dim]")

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer((host, port), QuietHandler)

    def serve() -> None:
        httpd.serve_forever()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    try:
        while True:
            time.sleep(0.3)
            if rebuild_flag[0]:
                rebuild_flag[0] = False
                console.print("[cyan]Rebuilding…[/cyan]")
                try:
                    Builder(content_root).build()
                    console.print("[green]Rebuild done[/green]")
                except SystemExit as exc:
                    console.print(f"[red]Rebuild failed:[/red] {exc}")
                except Exception as exc:  # noqa: BLE001
                    console.print(f"[red]Rebuild error:[/red] {exc}")
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/yellow]")
    finally:
        observer.stop()
        observer.join(timeout=2)
        httpd.shutdown()


if __name__ == "__main__":
    app()
