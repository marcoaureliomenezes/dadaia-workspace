"""Unit tests for ImportService."""

import io
import json
import tarfile
from pathlib import Path

import pytest

from dadaia_workspace.core.models.import_ import ImportOptions
from dadaia_workspace.features.import_.service import ImportService


def _make_archive(
    tmp_path: Path, *, with_manifest: bool = True, manifest_data: dict | None = None
) -> Path:
    archive = tmp_path / "ws.tar.gz"
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


def test_validate_returns_manifest(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    archive = _make_archive(tmp_path)
    manifest = svc.validate(archive)
    assert manifest.version == "1"
    assert manifest.workspace_root == "/old/ws"


def test_validate_rejects_archive_without_manifest(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    archive = _make_archive(tmp_path, with_manifest=False)
    with pytest.raises(ValueError, match="export-manifest"):
        svc.validate(archive)


def test_extract_creates_files(tmp_path: Path) -> None:
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


def test_patch_state_rewrites_specs_dir(tmp_path: Path) -> None:
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
    svc.patch_state(tmp_path, Path("/old/ws"))
    data = json.loads((states / "spec_contexts.json").read_text())
    ctx = data["contexts"][0]
    assert ctx["specs_dir"] == str(tmp_path / "repos" / "alpha" / "specs")
    assert ctx["state"] == "dead"
    assert "is_primary" not in ctx
    assert "activated_at" not in ctx
    assert ctx.get("dead_since") is None
    assert ctx.get("alive_since") is None


def test_patch_state_clears_primary_marker(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(json.dumps({"version": "1", "contexts": []}))
    (states / "primary_context.json").write_text(json.dumps({"name": "alpha"}))
    svc.patch_state(tmp_path, Path("/old/ws"))
    assert not (states / "primary_context.json").exists()


def test_dry_run_does_not_extract(tmp_path: Path) -> None:
    archive = _make_archive(tmp_path)
    dest = tmp_path / "fresh-ws"
    svc = ImportService(workspace_root=dest)
    result = svc.run(
        ImportOptions(archive=archive, workspace=dest, skip_activate=True, dry_run=True)
    )
    assert not (dest / ".dadaia").exists()
    assert result.workspace_root == dest


def test_validate_raises_when_archive_missing(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    with pytest.raises(ValueError, match="Archive not found"):
        svc.validate(tmp_path / "nonexistent.tar.gz")


def test_validate_raises_on_wrong_extension(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    wrong = tmp_path / "archive.zip"
    wrong.write_bytes(b"data")
    with pytest.raises(ValueError, match=".tar.gz"):
        svc.validate(wrong)


def test_validate_raises_on_missing_required_field(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    archive = _make_archive(
        tmp_path,
        manifest_data={
            "version": "1",
            "exported_at": "2026-01-01T00:00:00Z",
            # "workspace_root" missing
            "contexts": [],
        },
    )
    with pytest.raises(ValueError, match="workspace_root"):
        svc.validate(archive)


def test_extract_skips_env_files(tmp_path: Path) -> None:
    archive = tmp_path / "ws.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        safe = b"content"
        info1 = tarfile.TarInfo(".dadaia/states/ctx.json")
        info1.size = len(safe)
        tar.addfile(info1, io.BytesIO(safe))
        secret = b"SECRET=abc"
        info2 = tarfile.TarInfo(".env")
        info2.size = len(secret)
        tar.addfile(info2, io.BytesIO(secret))
    dest = tmp_path / "ws-out"
    svc = ImportService(workspace_root=dest)
    svc.extract(archive, dest, skip_mnt=False)
    assert (dest / ".dadaia" / "states" / "ctx.json").exists()
    assert not (dest / ".env").exists()  # .env was skipped


def test_patch_state_when_no_contexts_file(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    # No .dadaia/states/spec_contexts.json — should be a no-op
    svc.patch_state(tmp_path, Path("/old/ws"))  # must not raise


def test_patch_state_handles_non_dict_ctx(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": ["not_a_dict", 42]})
    )
    svc.patch_state(tmp_path, Path("/old/ws"))  # should handle non-dict entries silently


def test_patch_json_paths_rewrites_settings(tmp_path: Path) -> None:
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


def test_patch_json_paths_no_change_when_same_prefix(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings = {"hooks": {"PreToolUse": [{"script": str(tmp_path / "scripts" / "gate.sh")}]}}
    (claude_dir / "settings.json").write_text(json.dumps(settings))
    # Same old_root as workspace_root → no-op
    svc.patch_json_paths(tmp_path, tmp_path)
    result = json.loads((claude_dir / "settings.json").read_text())
    assert result == settings


def test_patch_json_paths_skips_missing_files(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    # Target files don't exist → no error
    svc.patch_json_paths(tmp_path, Path("/old/ws"))


def test_rewrite_paths_in_value_string_exact(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    result, count = svc._rewrite_paths_in_value("/old/ws", "/old/ws", "/new/ws")
    # Exact-match rebuilds to the host-native new root (see _string_prefix above).
    assert result == str(Path("/new/ws"))
    assert count == 1


def test_rewrite_paths_in_value_string_prefix(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    result, count = svc._rewrite_paths_in_value("/old/ws/scripts/run.sh", "/old/ws", "/new/ws")
    # Output is rebuilt host-native (str(Path(new) / rel)) so the rewrite works on
    # Windows where the stored "/"-paths would never match a "\"-separated str(root).
    assert result == str(Path("/new/ws") / "scripts" / "run.sh")
    assert count == 1


def test_rewrite_paths_in_value_non_matching(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    result, count = svc._rewrite_paths_in_value("/other/path/file.sh", "/old/ws", "/new/ws")
    assert result == "/other/path/file.sh"
    assert count == 0


def test_rewrite_paths_in_value_nested(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    value = {"a": ["/old/ws/x", "/other/path"], "b": {"c": "/old/ws/y"}}
    result, count = svc._rewrite_paths_in_value(value, "/old/ws", "/new/ws")
    assert count == 2
    assert result["a"][0] == str(Path("/new/ws") / "x")  # type: ignore[index]
    assert result["a"][1] == "/other/path"  # type: ignore[index]
    assert result["b"]["c"] == str(Path("/new/ws") / "y")  # type: ignore[index]


def test_restore_contexts_skip_true_returns_empty(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.import_ import ImportManifest

    svc = ImportService(workspace_root=tmp_path)
    manifest = ImportManifest(
        version="1",
        exported_at="2026-01-01T00:00:00Z",
        workspace_root="/old/ws",
        dadaia_version="0.1.0",
        contexts=(),
        includes=(),
        mnt_included=False,
        reports_included=False,
    )
    errors = svc.restore_contexts(manifest, tmp_path, skip=True)
    assert errors == ()


def test_restore_contexts_no_ativo_contexts_skip_false(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.import_ import ImportManifest

    svc = ImportService(workspace_root=tmp_path)
    manifest = ImportManifest(
        version="1",
        exported_at="2026-01-01T00:00:00Z",
        workspace_root="/old/ws",
        dadaia_version="0.1.0",
        contexts=({"name": "ctx1", "state": "inativo", "is_primary": False},),
        includes=(),
        mnt_included=False,
        reports_included=False,
    )
    # No ativo contexts → no subprocess calls, returns empty errors
    errors = svc.restore_contexts(manifest, tmp_path, skip=False)
    assert errors == ()


def test_run_full_path_without_activate(tmp_path: Path) -> None:
    from unittest.mock import patch

    svc = ImportService(workspace_root=tmp_path)
    archive = tmp_path / "ws.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        # Include the manifest
        manifest_data = {
            "version": "1",
            "exported_at": "2026-01-01T00:00:00Z",
            "workspace_root": "/old/ws",
            "dadaia_version": "0.1.0",
            "contexts": [],
            "includes": [".dadaia/states"],
            "mnt_included": False,
            "reports_included": False,
        }
        payload = json.dumps(manifest_data).encode()
        info = tarfile.TarInfo("export-manifest.json")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
        # Include a state file so extract creates .dadaia/
        ctx_payload = json.dumps({"version": "1", "contexts": []}).encode()
        info2 = tarfile.TarInfo(".dadaia/states/spec_contexts.json")
        info2.size = len(ctx_payload)
        tar.addfile(info2, io.BytesIO(ctx_payload))
    dest = tmp_path / "dest"
    from dadaia_workspace.core.models.import_ import ImportOptions

    options = ImportOptions(archive=archive, workspace=dest, skip_activate=True, dry_run=False)
    with patch.object(svc, "bootstrap") as mock_boot:
        mock_boot.return_value = None
        result = svc.run(options)
    assert (dest / ".dadaia").exists()
    mock_boot.assert_called_once_with(dest)
    assert result.contexts_restored == ()


def test_restore_contexts_activate_succeeds(tmp_path: Path) -> None:
    from unittest.mock import MagicMock, patch

    from dadaia_workspace.core.models.import_ import ImportManifest

    svc = ImportService(workspace_root=tmp_path)
    manifest = ImportManifest(
        version="1",
        exported_at="2026-01-01T00:00:00Z",
        workspace_root="/old/ws",
        dadaia_version="0.1.0",
        contexts=({"name": "ctx1", "state": "ativo", "is_primary": False},),
        includes=(),
        mnt_included=False,
        reports_included=False,
    )
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch(
        "dadaia_workspace.features.import_.service.subprocess.run", return_value=mock_result
    ):
        errors = svc.restore_contexts(manifest, tmp_path, skip=False)
    assert errors == ()


def test_restore_contexts_activate_fails(tmp_path: Path) -> None:
    from unittest.mock import MagicMock, patch

    from dadaia_workspace.core.models.import_ import ImportManifest

    svc = ImportService(workspace_root=tmp_path)
    manifest = ImportManifest(
        version="1",
        exported_at="2026-01-01T00:00:00Z",
        workspace_root="/old/ws",
        dadaia_version="0.1.0",
        contexts=({"name": "ctx1", "state": "ativo", "is_primary": False},),
        includes=(),
        mnt_included=False,
        reports_included=False,
    )
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "git clone failed"
    with patch(
        "dadaia_workspace.features.import_.service.subprocess.run", return_value=mock_result
    ):
        errors = svc.restore_contexts(manifest, tmp_path, skip=False)
    assert len(errors) == 1
    assert "ctx1" in errors[0]


# test_restore_contexts_with_primary_promote_fails was removed in v2:
# The v1 "promote" step (called after activate for is_primary=True contexts) no longer
# exists in v2 restore_contexts. v2 only activates; there is no primary/promote concept.
# The activate-fails path is already covered by test_restore_contexts_activate_fails.


def test_run_dry_run_prints_and_returns(tmp_path: Path) -> None:
    svc = ImportService(workspace_root=tmp_path)
    archive = _make_archive(
        tmp_path,
        manifest_data={
            "version": "1",
            "exported_at": "2026-01-01T00:00:00Z",
            "workspace_root": "/old/ws",
            "dadaia_version": "0.1.0",
            "contexts": [{"name": "ctx1", "state": "ativo", "is_primary": True}],
            "includes": [".dadaia/states"],
            "mnt_included": False,
            "reports_included": False,
        },
    )
    dest = tmp_path / "dry-dest"
    from dadaia_workspace.core.models.import_ import ImportOptions

    options = ImportOptions(archive=archive, workspace=dest, skip_activate=True, dry_run=True)
    result = svc.run(options)
    assert not (dest / ".dadaia").exists()
    assert result.workspace_root == dest
