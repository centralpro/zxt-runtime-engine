from __future__ import annotations

import html
import shutil
import subprocess
import tempfile
from pathlib import Path


class DiagramRenderError(RuntimeError):
    pass


def d2_available() -> bool:
    return shutil.which("d2") is not None


def render_d2(source: str, *, theme: int = 200) -> str:
    """Render D2 diagram source to an inline SVG block."""
    if not d2_available():
        raise DiagramRenderError(
            "D2 is not installed. Install: https://d2lang.com/ or `brew install d2`"
        )
    code = source.strip()
    if not code:
        raise DiagramRenderError("Empty D2 diagram")

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "diagram.d2"
        out = Path(tmp) / "diagram.svg"
        src.write_text(code, encoding="utf-8")
        proc = subprocess.run(
            [
                "d2",
                str(src),
                str(out),
                f"--theme={theme}",
                "--pad=28",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "unknown error").strip()
            raise DiagramRenderError(detail)
        svg = out.read_text(encoding="utf-8")
        if "<svg" not in svg:
            raise DiagramRenderError("D2 did not produce SVG output")

    return (
        '<figure class="diagram-block diagram-block--d2" role="figure" aria-label="示意图">'
        f"{svg}"
        "</figure>"
    )


def render_mermaid_fallback(source: str) -> str:
    """Client-rendered Mermaid (legacy). Prefer D2 for new diagrams."""
    return (
        '<div class="mermaid-block" role="figure" aria-label="流程图">'
        f'<pre class="mermaid">{html.escape(source.strip())}</pre>'
        "</div>"
    )
