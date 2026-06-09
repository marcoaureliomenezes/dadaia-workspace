"""Tests for UTF-8 encoding correctness in JSON store I/O and atomic write semantics.

Ensures that:
- ``_atomic_write_text`` round-trips non-ASCII content (e.g. accented chars,
  CJK characters) correctly via explicit UTF-8 encoding.
- ``_atomic_write_text`` is atomic: it uses ``os.replace`` under the hood, so
  writing to an already-existing destination file succeeds without error and
  produces the new content.
- JSON stores (JsonContextStore, JsonServerRegistryStore) round-trip non-ASCII
  data (paths, project names) correctly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from dadaia_workspace.infrastructure.public_assets_common import _atomic_write_text

# ---------------------------------------------------------------------------
# _atomic_write_text — core invariants
# ---------------------------------------------------------------------------


class TestAtomicWriteText:
    def test_roundtrip_ascii(self, tmp_path: Path) -> None:
        dst = tmp_path / "out.json"
        _atomic_write_text(dst, '{"key": "value"}')
        assert dst.read_text(encoding="utf-8") == '{"key": "value"}'

    def test_roundtrip_non_ascii_accented(self, tmp_path: Path) -> None:
        """Accented characters survive the write-read cycle."""
        content = '{"name": "café résumé"}'
        dst = tmp_path / "out.json"
        _atomic_write_text(dst, content)
        assert dst.read_text(encoding="utf-8") == content

    def test_roundtrip_cjk(self, tmp_path: Path) -> None:
        """CJK characters survive the write-read cycle."""
        content = '{"label": "日本語テスト"}'
        dst = tmp_path / "out.json"
        _atomic_write_text(dst, content)
        assert dst.read_text(encoding="utf-8") == content

    def test_roundtrip_mixed_non_ascii(self, tmp_path: Path) -> None:
        """Mixed Latin-extended and CJK in a single payload."""
        content = '{"path": "café/日本語", "desc": "résumé — テスト"}'
        dst = tmp_path / "out.json"
        _atomic_write_text(dst, content)
        assert dst.read_text(encoding="utf-8") == content

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Atomic write to an existing destination overwrites it without error."""
        dst = tmp_path / "state.json"
        dst.write_text('{"version": 1}', encoding="utf-8")

        _atomic_write_text(dst, '{"version": 2}')

        assert dst.read_text(encoding="utf-8") == '{"version": 2}'

    def test_uses_os_replace_not_os_rename(self, tmp_path: Path) -> None:
        """_atomic_write_text calls os.replace (not os.rename) for the swap step."""
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

    def test_tmp_file_removed_after_write(self, tmp_path: Path) -> None:
        """The .tmp sibling file is gone after a successful write."""
        dst = tmp_path / "data.json"
        _atomic_write_text(dst, "{}")
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        assert not tmp.exists(), ".tmp sibling should be cleaned up by os.replace"

    def test_writes_utf8_bytes_on_disk(self, tmp_path: Path) -> None:
        """The file on disk is valid UTF-8 (no BOM, correct byte representation)."""
        content = "café/日本語"
        dst = tmp_path / "raw.txt"
        _atomic_write_text(dst, content)
        raw = dst.read_bytes()
        assert raw.decode("utf-8") == content
        # Confirm no UTF-8 BOM
        assert not raw.startswith(b"\xef\xbb\xbf")


# ---------------------------------------------------------------------------
# JSON store round-trip with non-ASCII data
# ---------------------------------------------------------------------------


class TestJsonContextStoreNonAscii:
    """JsonContextStore persists and retrieves non-ASCII context data."""

    @staticmethod
    def _make_ctx(name: str, repo_slug: str = "test-repo") -> object:
        from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

        return SpecContextProject(
            name=name,
            state=ContextState.ALIVE,
            repo_slug=repo_slug,
            repo_url="https://github.com/example/test-repo",
            created_at="2026-06-09T00:00:00Z",
        )

    def test_roundtrip_non_ascii_name(self, tmp_path: Path) -> None:
        """Context names with non-ASCII chars survive the save-list cycle."""
        from dadaia_workspace.infrastructure.json_context_store import JsonContextStore

        states_dir = tmp_path / "states"
        states_dir.mkdir()
        store = JsonContextStore(states_dir)

        name = "projet-café"
        store.save(self._make_ctx(name))

        contexts = store.list_all()
        assert any(c.name == name for c in contexts), "Context name should survive round-trip"

    def test_store_file_is_valid_utf8(self, tmp_path: Path) -> None:
        from dadaia_workspace.infrastructure.json_context_store import JsonContextStore

        states_dir = tmp_path / "states"
        states_dir.mkdir()
        store = JsonContextStore(states_dir)

        store.save(self._make_ctx("日本語テスト"))

        state_file = states_dir / "spec_contexts.json"
        raw = state_file.read_bytes()
        decoded = raw.decode("utf-8")  # must not raise
        data = json.loads(decoded)
        assert "contexts" in data


class TestJsonServerRegistryStoreNonAscii:
    """JsonServerRegistryStore persists and retrieves non-ASCII project names."""

    def test_roundtrip_non_ascii_project_name(self, tmp_path: Path) -> None:
        from dadaia_workspace.core.models.server_registry import PortEntry
        from dadaia_workspace.infrastructure.json_server_registry_store import (
            JsonServerRegistryStore,
        )

        states_dir = tmp_path / "states"
        states_dir.mkdir()
        store = JsonServerRegistryStore(states_dir)

        entry = PortEntry(
            port=3100,
            project="café-résumé-テスト",
            reserved_at="2026-06-09T00:00:00Z",
            expires_at="2026-06-09T08:00:00Z",
            url="http://localhost:3100",
        )
        store.save(entry)

        all_entries = store.list_all()
        assert any(e.project == "café-résumé-テスト" for e in all_entries)

    def test_store_file_is_valid_utf8(self, tmp_path: Path) -> None:
        from dadaia_workspace.core.models.server_registry import PortEntry
        from dadaia_workspace.infrastructure.json_server_registry_store import (
            JsonServerRegistryStore,
        )

        states_dir = tmp_path / "states"
        states_dir.mkdir()
        store = JsonServerRegistryStore(states_dir)

        store.save(
            PortEntry(
                port=3200,
                project="日本語プロジェクト",
                reserved_at="2026-06-09T00:00:00Z",
                expires_at="2026-06-09T08:00:00Z",
                url="http://localhost:3200",
            )
        )

        state_file = states_dir / "server_registry.json"
        raw = state_file.read_bytes()
        raw.decode("utf-8")  # must not raise — verifies UTF-8 encoding on disk
