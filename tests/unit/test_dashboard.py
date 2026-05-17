"""Unit tests for dashboard.render_html()."""

import json
from pathlib import Path

from dadaia_workspace.features.server_registry.dashboard import render_html


def _write_registry(path: Path, entries: list[dict]) -> None:  # type: ignore[type-arg]
    registry = {
        "version": "1",
        "range": {"min_port": 3000, "max_port": 3999},
        "entries": entries,
    }
    (path / "server_registry.json").write_text(json.dumps(registry))


def test_render_html_shows_project_name(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "port": 3000,
                "project": "redacted-slug",
                "url": "http://localhost:3000",
                "status": "active",
                "pid": None,
                "reserved_at": "2026-05-16T10:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "description": None,
            }
        ],
    )
    html = render_html(tmp_path)
    assert "redacted-slug" in html


def test_render_html_shows_clickable_url(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "port": 3000,
                "project": "redacted-slug",
                "url": "http://localhost:3000",
                "status": "active",
                "pid": None,
                "reserved_at": "2026-05-16T10:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "description": None,
            }
        ],
    )
    html = render_html(tmp_path)
    assert 'href="http://localhost:3000"' in html
    assert "http://localhost:3000" in html


def test_render_html_empty_registry_shows_message(tmp_path: Path) -> None:
    _write_registry(tmp_path, [])
    html = render_html(tmp_path)
    assert "No servers registered" in html


def test_render_html_no_file_shows_message(tmp_path: Path) -> None:
    html = render_html(tmp_path)
    assert "No servers registered" in html


def test_render_html_includes_auto_refresh(tmp_path: Path) -> None:
    _write_registry(tmp_path, [])
    html = render_html(tmp_path)
    assert 'http-equiv="refresh"' in html
    assert 'content="5"' in html


def test_render_html_shows_description_when_present(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "port": 3000,
                "project": "redacted-slug",
                "url": "http://localhost:3000",
                "status": "active",
                "pid": None,
                "reserved_at": "2026-05-16T10:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "description": "Vite dev server",
            }
        ],
    )
    html = render_html(tmp_path)
    assert "Vite dev server" in html
