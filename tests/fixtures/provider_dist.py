"""A fake ``dadaia-workspace`` distribution at the importlib.metadata boundary — the one
seam ``infrastructure.provider_version`` reads (dist-info version + ``direct_url.json``)."""

from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

import pytest


class _Dist:
    files = None  # no RECORD payload: build_digest of nothing

    def __init__(self, version: str, direct_url: dict[str, object] | None) -> None:
        self.version = version
        self._direct = json.dumps(direct_url) if direct_url else None

    def read_text(self, name: str) -> str | None:
        return self._direct if name == "direct_url.json" else None


def install_fake_dist(
    monkeypatch: pytest.MonkeyPatch, version: str, *, editable_source: Path | None = None
) -> None:
    """dist-info at *version*; with *editable_source*, an editable install of that tree."""
    direct = (
        {"dir_info": {"editable": True}, "url": editable_source.as_uri()}
        if editable_source
        else None
    )
    monkeypatch.setattr(metadata, "distribution", lambda name: _Dist(version, direct))
