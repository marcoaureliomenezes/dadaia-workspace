"""The running dadaia-workspace version — the ONE reader of it."""

from __future__ import annotations

import json
import re
from importlib import metadata
from pathlib import Path
from urllib.request import url2pathname


def provider_version() -> str | None:
    """The dist-info version, except an editable install (its dist-info freezes at install
    time): the source ``pyproject.toml`` version. ``None`` when not installed."""
    try:
        dist = metadata.distribution("dadaia-workspace")
    except metadata.PackageNotFoundError:
        return None
    try:
        direct = json.loads(dist.read_text("direct_url.json") or "{}")
    except ValueError:
        direct = {}
    url = str(direct.get("url", ""))
    if (direct.get("dir_info") or {}).get("editable") and url.startswith("file://"):
        pyproject = Path(url2pathname(url.removeprefix("file://"))) / "pyproject.toml"
        text = pyproject.read_text("utf-8") if pyproject.is_file() else ""
        if found := re.search(r'^version\s*=\s*"([^"]+)"', text, re.M):
            return found.group(1)
    return dist.version
