"""Unit tests for ImportService.

CRIT: the `.env`-skip test is a secret exfil guard — kept standalone, never merged away.
"""

import io
import json
import tarfile
from collections.abc import Sequence
from pathlib import Path

import pytest

from dadaia_workspace.core.models.import_ import ImportManifest, ImportOptions
from dadaia_workspace.core.protocols.process_runner import ProcessResult
from dadaia_workspace.features.import_.service import ImportService


class _FakeProcessRunner:
    """Fake ProcessRunner for injection into ImportService."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self._result = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> ProcessResult:
        return self._result


def _make_archive(
    tmp_path: Path,
    *,
    with_manifest: bool = True,
    manifest_data: dict | None = None,
    filename: str = "ws.tar.gz",
) -> Path:
    archive = tmp_path / filename
    with tarfile.open(archive, "w:gz") as tar:
        if with_manifest:
            payload = json.dumps(
                manifest_data
                or {
                    "version": "1",
                    "exported_at": "2026-01-01T00:00:00Z",
                    "workspace_root": "/old/ws",
                    "dadaia_version": "0.1.0",
                    "contexts": [],
                    "includes": [".dadaia/states"],
                    "mnt_included": False,
                    "reports_included": False,
                }
            ).encode()
            info = tarfile.TarInfo("export-manifest.json")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        else:
            payload = b"hi"
            info = tarfile.TarInfo("hello.txt")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    return archive


def _default_manifest_data() -> dict:
    return {
        "version": "1",
        "exported_at": "2026-01-01T00:00:00Z",
        "workspace_root": "/old/ws",
        "dadaia_version": "0.1.0",
        "contexts": [],
        "includes": [".dadaia/states"],
        "mnt_included": False,
        "reports_included": False,
    }


# ---------------------------------------------------------------------------
# validate() — ok + every rejection path
# ---------------------------------------------------------------------------


def test_validate_table(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)

    ok_archive = _make_archive(tmp_path, filename="ok.tar.gz")
    manifest = svc.validate(ok_archive)
    assert manifest.version == "1"
    assert manifest.workspace_root == "/old/ws"

    no_manifest_archive = _make_archive(
        tmp_path, with_manifest=False, filename="no-manifest.tar.gz"
    )
    with pytest.raises(ValueError, match="export-manifest"):
        svc.validate(no_manifest_archive)

    with pytest.raises(ValueError, match="Archive not found"):
        svc.validate(tmp_path / "nonexistent.tar.gz")

    wrong_ext = tmp_path / "archive.zip"
    wrong_ext.write_bytes(b"data")
    with pytest.raises(ValueError, match=".tar.gz"):
        svc.validate(wrong_ext)

    missing_field_archive = _make_archive(
        tmp_path,
        manifest_data={
            "version": "1",
            "exported_at": "2026-01-01T00:00:00Z",
            # "workspace_root" missing
            "contexts": [],
        },
        filename="missing-field.tar.gz",
    )
    with pytest.raises(ValueError, match="workspace_root"):
        svc.validate(missing_field_archive)


# ---------------------------------------------------------------------------
# extract() — creates files, skips .env (CRIT secret exfil guard)
# ---------------------------------------------------------------------------


def test_extract_creates_files_and_skips_env_files(tmp_path: Path) -> None:
    archive = tmp_path / "ws.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        payload = b"content"
        info = tarfile.TarInfo(".dadaia/states/spec_contexts.json")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    dest = tmp_path / "ws-out"
    svc = ImportService(workspace_root=dest)
    svc.extract(archive, dest, skip_mnt=False)
    assert (dest / ".dadaia" / "states" / "spec_contexts.json").read_text() == "content"

    # CRIT: `.env` never lands in an imported workspace — a secret exfil guard.
    archive2 = tmp_path / "ws-env.tar.gz"
    with tarfile.open(archive2, "w:gz") as tar2:
        safe = b"content"
        info1 = tarfile.TarInfo(".dadaia/states/ctx.json")
        info1.size = len(safe)
        tar2.addfile(info1, io.BytesIO(safe))
        secret = b"SECRET=abc"
        info2 = tarfile.TarInfo(".env")
        info2.size = len(secret)
        tar2.addfile(info2, io.BytesIO(secret))
    dest2 = tmp_path / "ws-out-env"
    svc2 = ImportService(workspace_root=dest2)
    svc2.extract(archive2, dest2, skip_mnt=False)
    assert (dest2 / ".dadaia" / "states" / "ctx.json").exists()
    assert not (dest2 / ".env").exists()  # .env was skipped


def test_extract_relocates_export_manifest_off_the_root(tmp_path: Path) -> None:
    """Bug import-extracts-manifest-to-root (validation F-16): archive metadata must
    never land at the workspace root — the imported workspace has to pass the tool's
    own doctor (ROOT-1). Provenance is preserved under .dadaia/states/."""
    archive = tmp_path / "ws.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        manifest = b'{"version": "1"}'
        info = tarfile.TarInfo("export-manifest.json")
        info.size = len(manifest)
        tar.addfile(info, io.BytesIO(manifest))
        payload = b"content"
        info2 = tarfile.TarInfo(".dadaia/states/spec_contexts.json")
        info2.size = len(payload)
        tar.addfile(info2, io.BytesIO(payload))
    dest = tmp_path / "ws-out"
    svc = ImportService(workspace_root=dest)
    svc.extract(archive, dest, skip_mnt=False)
    assert not (dest / "export-manifest.json").exists()
    assert (dest / ".dadaia" / "states" / "import-manifest.json").read_bytes() == (
        b'{"version": "1"}'
    )


# ---------------------------------------------------------------------------
# patch_state() — rewrite + clears-primary / no-file / non-dict entries
# ---------------------------------------------------------------------------


def test_patch_state_rewrites_and_clears_primary(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "version": "1",
                "contexts": [
                    {
                        "name": "alpha",
                        "state": "ativo",
                        "is_primary": True,
                        "specs_dir": "/old/ws/repos/alpha/specs",
                        "activated_at": "2026-01-01",
                    }
                ],
            }
        )
    )
    (states / "primary_context.json").write_text(json.dumps({"name": "alpha"}))

    svc.patch_state(tmp_path, Path("/old/ws"))

    data = json.loads((states / "spec_contexts.json").read_text())
    ctx = data["contexts"][0]
    assert ctx["specs_dir"] == str(tmp_path / "repos" / "alpha" / "specs")
    assert ctx["state"] == "dead"
    assert "is_primary" not in ctx
    assert "activated_at" not in ctx
    assert ctx.get("dead_since") is None
    assert ctx.get("alive_since") is None
    assert not (states / "primary_context.json").exists()

    # No .dadaia/states/spec_contexts.json in a fresh workspace — a no-op, must not raise.
    empty_ws = tmp_path.parent / (tmp_path.name + "-empty")
    empty_svc = ImportService(workspace_root=empty_ws)
    empty_svc.patch_state(empty_ws, Path("/old/ws"))

    # Non-dict context entries are handled silently (no crash).
    empty_states = empty_ws / ".dadaia" / "states"
    empty_states.mkdir(parents=True)
    (empty_states / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": ["not_a_dict", 42]})
    )
    empty_svc.patch_state(empty_ws, Path("/old/ws"))


# ---------------------------------------------------------------------------
# patch_json_paths() — rewrites settings, no-op on same prefix, skips missing files
# ---------------------------------------------------------------------------


def test_patch_json_paths_table(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    old_ws = "/old/workspace"
    settings = {
        "hooks": {
            "PreToolUse": [{"script": f"{old_ws}/.claude/scripts/gate.sh"}],
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings))
    svc.patch_json_paths(tmp_path, Path(old_ws))
    result = json.loads((claude_dir / "settings.json").read_text())
    hook_script = result["hooks"]["PreToolUse"][0]["script"]
    assert hook_script == str(tmp_path / ".claude" / "scripts" / "gate.sh")

    # Same old_root as workspace_root → no-op.
    same_prefix_settings = {
        "hooks": {"PreToolUse": [{"script": str(tmp_path / "scripts" / "gate.sh")}]}
    }
    (claude_dir / "settings.json").write_text(json.dumps(same_prefix_settings))
    svc.patch_json_paths(tmp_path, tmp_path)
    unchanged = json.loads((claude_dir / "settings.json").read_text())
    assert unchanged == same_prefix_settings

    # Target files don't exist → no error.
    empty_dest = tmp_path / "no-claude-dir"
    empty_svc = ImportService(workspace_root=empty_dest)
    empty_svc.patch_json_paths(empty_dest, Path("/old/ws"))


# ---------------------------------------------------------------------------
# _rewrite_paths_in_value() — exact / prefix / non-matching / nested
# ---------------------------------------------------------------------------


def test_rewrite_paths_in_value_table(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)

    # Exact-match rebuilds to the host-native new root (see _string_prefix above).
    exact_result, exact_count = svc._rewrite_paths_in_value("/old/ws", "/old/ws", "/new/ws")
    assert exact_result == str(Path("/new/ws"))
    assert exact_count == 1

    # Output is rebuilt host-native (str(Path(new) / rel)) so the rewrite works on
    # Windows where the stored "/"-paths would never match a "\"-separated str(root).
    prefix_result, prefix_count = svc._rewrite_paths_in_value(
        "/old/ws/scripts/run.sh", "/old/ws", "/new/ws"
    )
    assert prefix_result == str(Path("/new/ws") / "scripts" / "run.sh")
    assert prefix_count == 1

    non_match_result, non_match_count = svc._rewrite_paths_in_value(
        "/other/path/file.sh", "/old/ws", "/new/ws"
    )
    assert non_match_result == "/other/path/file.sh"
    assert non_match_count == 0

    value = {"a": ["/old/ws/x", "/other/path"], "b": {"c": "/old/ws/y"}}
    nested_result, nested_count = svc._rewrite_paths_in_value(value, "/old/ws", "/new/ws")
    assert nested_count == 2
    assert nested_result["a"][0] == str(Path("/new/ws") / "x")  # type: ignore[index]
    assert nested_result["a"][1] == "/other/path"  # type: ignore[index]
    assert nested_result["b"]["c"] == str(Path("/new/ws") / "y")  # type: ignore[index]


# ---------------------------------------------------------------------------
# restore_contexts() — skip, no-ativo, activate succeeds, activate fails
# ---------------------------------------------------------------------------


def test_restore_contexts_skip_no_ativo_and_activate_succeeds_and_fails(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)

    skip_manifest = ImportManifest(
        version="1",
        exported_at="2026-01-01T00:00:00Z",
        workspace_root="/old/ws",
        dadaia_version="0.1.0",
        contexts=(),
        includes=(),
        mnt_included=False,
        reports_included=False,
    )
    assert svc.restore_contexts(skip_manifest, tmp_path, skip=True) == ()

    inativo_manifest = ImportManifest(
        version="1",
        exported_at="2026-01-01T00:00:00Z",
        workspace_root="/old/ws",
        dadaia_version="0.1.0",
        contexts=({"name": "ctx1", "state": "inativo", "is_primary": False},),
        includes=(),
        mnt_included=False,
        reports_included=False,
    )
    # No ativo contexts → no subprocess calls, returns empty errors.
    assert svc.restore_contexts(inativo_manifest, tmp_path, skip=False) == ()

    ativo_manifest = ImportManifest(
        version="1",
        exported_at="2026-01-01T00:00:00Z",
        workspace_root="/old/ws",
        dadaia_version="0.1.0",
        contexts=({"name": "ctx1", "state": "ativo", "is_primary": False},),
        includes=(),
        mnt_included=False,
        reports_included=False,
    )

    success_svc = ImportService(
        workspace_root=tmp_path, process_runner=_FakeProcessRunner(returncode=0)
    )
    assert success_svc.restore_contexts(ativo_manifest, tmp_path, skip=False) == ()

    fail_svc = ImportService(
        workspace_root=tmp_path,
        process_runner=_FakeProcessRunner(returncode=1, stderr="git clone failed"),
    )
    errors = fail_svc.restore_contexts(ativo_manifest, tmp_path, skip=False)
    assert len(errors) == 1
    assert "ctx1" in errors[0]


def test_bootstrap_raises_runtime_error_on_nonzero_exit(tmp_path: Path) -> None:
    """bootstrap() must raise RuntimeError when `dadaia init` exits non-zero, so the
    CLI's (ValueError, RuntimeError) handler surfaces a clean message instead of an
    uncaught traceback (T-CODE-01 regression guard: the old subprocess.run(check=True)
    raised CalledProcessError; the adapter path now maps non-zero to RuntimeError)."""
    svc = ImportService(
        workspace_root=tmp_path,
        process_runner=_FakeProcessRunner(returncode=2, stderr="init failed"),
    )
    with pytest.raises(RuntimeError, match="dadaia init failed"):
        svc.bootstrap(tmp_path)


# ---------------------------------------------------------------------------
# run() — full path (bootstrap called), dry-run (never extracts)
# ---------------------------------------------------------------------------


def test_run_full_path_without_activate(tmp_path: Path) -> None:
    from unittest.mock import patch

    svc = ImportService(workspace_root=tmp_path)
    archive = tmp_path / "ws.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        payload = json.dumps(_default_manifest_data()).encode()
        info = tarfile.TarInfo("export-manifest.json")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
        # Include a state file so extract creates .dadaia/
        ctx_payload = json.dumps({"version": "1", "contexts": []}).encode()
        info2 = tarfile.TarInfo(".dadaia/states/spec_contexts.json")
        info2.size = len(ctx_payload)
        tar.addfile(info2, io.BytesIO(ctx_payload))
    dest = tmp_path / "dest"

    options = ImportOptions(archive=archive, workspace=dest, skip_activate=True, dry_run=False)
    with patch.object(svc, "bootstrap") as mock_boot:
        mock_boot.return_value = None
        result = svc.run(options)
    assert (dest / ".dadaia").exists()
    mock_boot.assert_called_once_with(dest)
    assert result.contexts_restored == ()


def test_run_dry_run_never_extracts(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    archive = _make_archive(
        tmp_path,
        manifest_data={
            **_default_manifest_data(),
            "contexts": [{"name": "ctx1", "state": "ativo", "is_primary": True}],
        },
        filename="dry.tar.gz",
    )
    dest = tmp_path / "dry-dest"

    options = ImportOptions(archive=archive, workspace=dest, skip_activate=True, dry_run=True)
    result = svc.run(options)
    assert not (dest / ".dadaia").exists()
    assert result.workspace_root == dest
