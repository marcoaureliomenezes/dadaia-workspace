"""Tests for UTF-8 encoding correctness in JSON store I/O and atomic write semantics.

Ensures that:
- ``_atomic_write_text`` round-trips non-ASCII content (e.g. accented chars,
  CJK characters) correctly via explicit UTF-8 encoding, including a rewrite over
  an already-existing destination (atomic overwrite).
- ``_atomic_write_text`` is atomic: it uses ``os.replace`` under the hood (never
  ``os.rename``), and the ``.tmp`` sibling is cleaned up after a successful write.
- JSON stores (JsonContextStore, JsonServerRegistryStore) round-trip non-ASCII
  data (paths, project names) correctly and the files on disk are valid UTF-8.

This is the SOLE owner of ``_atomic_write_text`` coverage in the suite (the
duplicate atomic-write tests formerly in ``test_public_assets.py`` were merged
here).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text


@pytest.mark.parametrize(
    "content",
    [
        pytest.param('{"key": "value"}', id="ascii"),
        pytest.param('{"name": "café résumé"}', id="accented"),
        pytest.param('{"label": "日本語テスト"}', id="cjk"),
        pytest.param('{"path": "café/日本語", "desc": "résumé — テスト"}', id="mixed-non-ascii"),
        pytest.param("café/日本語", id="raw-utf8-bytes-no-bom"),
    ],
)
def test_atomic_write_text_roundtrips_utf8(tmp_path: Path, content: str) -> None:
    dst = tmp_path / "out.json"
    _atomic_write_text(dst, content)
    assert dst.read_text(encoding="utf-8") == content
    raw = dst.read_bytes()
    assert raw.decode("utf-8") == content
    assert not raw.startswith(b"\xef\xbb\xbf"), "must not write a UTF-8 BOM"

    # Atomic overwrite: rewriting an already-existing destination succeeds cleanly.
    _atomic_write_text(dst, content + " ")
    assert dst.read_text(encoding="utf-8") == content + " "


def test_uses_os_replace_not_os_rename_and_cleans_up_tmp_sibling(tmp_path: Path) -> None:
    """_atomic_write_text calls os.replace (not os.rename) for the swap step, and
    the .tmp sibling file is gone after a successful write."""
    dst = tmp_path / "out.json"
    replace_calls: list[tuple[str, str]] = []

    original_replace = os.replace

    def tracking_replace(src: str, dst_: str) -> None:  # type: ignore[misc]
        replace_calls.append((str(src), str(dst_)))
        original_replace(src, dst_)

    with patch(
        "dadaia_workspace.infrastructure.public_assets_common.os.replace",
        tracking_replace,
    ):
        _atomic_write_text(dst, '{"x": 1}')

    assert len(replace_calls) == 1, "os.replace should be called exactly once"
    _src, _dst = replace_calls[0]
    assert _dst == str(dst), "os.replace destination should be the target path"
    assert _src.endswith(".tmp"), "os.replace source should be the .tmp sibling"

    tmp = dst.with_suffix(dst.suffix + ".tmp")
    assert not tmp.exists(), ".tmp sibling should be cleaned up by os.replace"


# ---------------------------------------------------------------------------
# JSON store round-trip with non-ASCII data
# ---------------------------------------------------------------------------


def _make_ctx(name: str, repo_slug: str = "test-repo") -> object:
    from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE,
        repo_slug=repo_slug,
        repo_url="https://github.com/example/test-repo",
        created_at="2026-06-09T00:00:00Z",
    )


def test_json_context_store_roundtrips_non_ascii_and_valid_utf8(tmp_path: Path) -> None:
    from dadaia_workspace.infrastructure.json_context_store import JsonContextStore

    states_dir = tmp_path / "states"
    states_dir.mkdir()
    store = JsonContextStore(states_dir)

    name = "projet-café"
    store.save(_make_ctx(name))
    store.save(_make_ctx("日本語テスト", repo_slug="jp-repo"))

    contexts = store.list_all()
    assert any(c.name == name for c in contexts), "Context name should survive round-trip"
    assert any(c.name == "日本語テスト" for c in contexts)

    state_file = states_dir / "spec_contexts.json"
    raw = state_file.read_bytes()
    decoded = raw.decode("utf-8")  # must not raise
    data = json.loads(decoded)
    assert "contexts" in data


def test_json_server_registry_store_roundtrips_non_ascii_and_valid_utf8(
    tmp_path: Path,
) -> None:
    from dadaia_workspace.core.models.server_registry import PortEntry
    from dadaia_workspace.infrastructure.json_server_registry_store import (
        JsonServerRegistryStore,
    )

    states_dir = tmp_path / "states"
    states_dir.mkdir()
    store = JsonServerRegistryStore(states_dir)

    store.save(
        PortEntry(
            port=3100,
            project="café-résumé-テスト",
            reserved_at="2026-06-09T00:00:00Z",
            expires_at="2026-06-09T08:00:00Z",
            url="http://localhost:3100",
        )
    )
    store.save(
        PortEntry(
            port=3200,
            project="日本語プロジェクト",
            reserved_at="2026-06-09T00:00:00Z",
            expires_at="2026-06-09T08:00:00Z",
            url="http://localhost:3200",
        )
    )

    all_entries = store.list_all()
    assert any(e.project == "café-résumé-テスト" for e in all_entries)
    assert any(e.project == "日本語プロジェクト" for e in all_entries)

    state_file = states_dir / "server_registry.json"
    raw = state_file.read_bytes()
    raw.decode("utf-8")  # must not raise — verifies UTF-8 encoding on disk
