"""Syntax smoke test for the inline browser JavaScript served by the app."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest


def test_inline_ui_javascript_passes_node_syntax_check(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed; browser JavaScript syntax check unavailable.")

    repository_root = Path(__file__).resolve().parents[1]
    html = (repository_root / "app" / "ui.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, flags=re.DOTALL)
    assert scripts, "Expected at least one inline script in app/ui.html"

    script_path = tmp_path / "ui.js"
    script_path.write_text("\\n".join(scripts), encoding="utf-8")
    result = subprocess.run(
        [node, "--check", str(script_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
