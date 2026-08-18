"""FR27 (v0.4.3 T-043-42) — the single shared JSONL log-rotation helper.

Intent: CONTRACT — A27.1, A27.2

``append_rotating_jsonl`` is the ONE implementation every ``.dadaia/logs/*.jsonl``
appender (``hooks/pre_gate.py``, ``hooks/sdd_post_gate.py``,
``features/chokepoints/service.py``'s push-verdict-gc ledger) funnels through, so the
~1 MB cap + current+1 retention rule (FR27) exists exactly once. These fixtures drive
the helper directly against a synthetic ``tmp_path`` file — no hook/gate wiring here
(that lives in each writer's own test file). The concurrent-writer fixture (A27.3) is a
SEPARATE integration-tier test (``tests/integration/infrastructure/
test_jsonl_log_rotation_concurrency.py``) since it spawns real OS processes.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.jsonl_log_rotation import (
    LOG_ROTATION_MAX_BYTES,
    append_rotating_jsonl,
)

pytestmark = pytest.mark.unit


def _lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]


# ---------------------------------------------------------------------------
# A27.1 — a log crossing the cap rotates; exactly one rotated file is retained.
# ---------------------------------------------------------------------------


def test_under_cap_appends_without_rotating(tmp_path: Path) -> None:
    log = tmp_path / "sample.jsonl"
    assert append_rotating_jsonl(log, json.dumps({"n": 1}), max_bytes=1_000_000) is True
    assert append_rotating_jsonl(log, json.dumps({"n": 2}), max_bytes=1_000_000) is True

    assert _lines(log) == [json.dumps({"n": 1}), json.dumps({"n": 2})]
    assert not log.with_name(log.name + ".1").exists()


def test_crossing_cap_rotates_current_to_dot_one(tmp_path: Path) -> None:
    log = tmp_path / "sample.jsonl"
    # Seed a "current" file already AT the cap so the very next append rotates it.
    log.write_text(json.dumps({"seed": True}) + "\n", encoding="utf-8")

    assert append_rotating_jsonl(log, json.dumps({"after": 1}), max_bytes=8) is True

    rotated = log.with_name(log.name + ".1")
    assert rotated.exists()
    assert _lines(rotated) == [json.dumps({"seed": True})]
    # The new current file holds ONLY the line written after rotation.
    assert _lines(log) == [json.dumps({"after": 1})]


def test_old_dot_one_dies_on_a_second_rotation(tmp_path: Path) -> None:
    log = tmp_path / "sample.jsonl"
    rotated = log.with_name(log.name + ".1")
    rotated.write_text(json.dumps({"generation": "stale"}) + "\n", encoding="utf-8")
    log.write_text(json.dumps({"generation": "current"}) + "\n", encoding="utf-8")

    assert append_rotating_jsonl(log, json.dumps({"generation": "new"}), max_bytes=8) is True

    # current+1 retention: the OLD .1 (generation=stale) is gone, replaced by the file
    # that WAS current (generation=current) — never more than one rotated generation.
    assert _lines(rotated) == [json.dumps({"generation": "current"})]
    assert _lines(log) == [json.dumps({"generation": "new"})]


def test_default_cap_matches_the_kernel_tunable() -> None:
    from dadaia_workspace.core.kernel_tunables import LOG_ROTATION_MAX_BYTES as tunable

    assert tunable == LOG_ROTATION_MAX_BYTES
    assert isinstance(LOG_ROTATION_MAX_BYTES, int)
    assert LOG_ROTATION_MAX_BYTES > 0


# ---------------------------------------------------------------------------
# A27.2 — a rotation error never changes a gate verdict: the helper itself never
# raises; every OSError is swallowed and reported as a plain ``False``.
# ---------------------------------------------------------------------------


def test_unwritable_parent_dir_is_fail_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "no-such-parent" / "sample.jsonl"

    def boom(*_a: object, **_k: object) -> None:
        raise OSError("parent unwritable")

    monkeypatch.setattr(Path, "mkdir", boom)
    assert append_rotating_jsonl(log, json.dumps({"x": 1})) is False


def test_append_target_already_a_directory_is_fail_open(tmp_path: Path) -> None:
    log = tmp_path / "sample.jsonl"
    log.mkdir()  # the "file" is actually a directory -> open(..., "a") raises

    assert append_rotating_jsonl(log, json.dumps({"x": 1})) is False
    assert log.is_dir()  # untouched — no crash, no partial write


@pytest.mark.skipif(
    sys.platform == "win32", reason="chmod-based read-only-file probe is POSIX-only"
)
def test_readonly_target_file_is_fail_open(tmp_path: Path) -> None:
    log = tmp_path / "sample.jsonl"
    log.write_text(json.dumps({"seed": True}) + "\n", encoding="utf-8")

    original_mode = log.stat().st_mode
    os.chmod(log, stat.S_IRUSR)
    try:
        result = append_rotating_jsonl(log, json.dumps({"x": 1}))
    finally:
        os.chmod(log, original_mode)

    assert result is False
    assert _lines(log) == [json.dumps({"seed": True})]


@pytest.mark.skipif(
    sys.platform == "win32", reason="chmod-based unwritable-dir probe is POSIX-only"
)
def test_readonly_logs_dir_blocks_rotation_but_append_still_lands(tmp_path: Path) -> None:
    """When the cap IS crossed but the containing dir is read-only, both the lock
    (``mkdir``) and the rotation (``os.replace``) fail — fail-open (A27.2) means the
    line still lands in the un-rotated file rather than being silently dropped; the
    ONLY thing that fails to happen is the rotation itself, exactly the "at most cap +
    slack" allowance A27.3 describes.
    """
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    log = logs_dir / "sample.jsonl"
    log.write_text(json.dumps({"seed": True}) + "\n", encoding="utf-8")

    original_mode = logs_dir.stat().st_mode
    os.chmod(logs_dir, stat.S_IRUSR | stat.S_IXUSR)
    try:
        result = append_rotating_jsonl(log, json.dumps({"after": 1}), max_bytes=8)
    finally:
        os.chmod(logs_dir, original_mode)

    assert result is True
    assert not log.with_name(log.name + ".1").exists()
    assert _lines(log) == [json.dumps({"seed": True}), json.dumps({"after": 1})]


# ---------------------------------------------------------------------------
# Stale-lock self-healing — a crashed holder's abandoned lock dir never permanently
# stalls rotation for future callers (defense in depth for A27.2/A27.3).
# ---------------------------------------------------------------------------


def test_stale_lock_directory_is_reclaimed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dadaia_workspace.infrastructure import jsonl_log_rotation as mod

    log = tmp_path / "sample.jsonl"
    log.write_text(json.dumps({"seed": True}) + "\n", encoding="utf-8")
    lock_dir = mod._lock_dir_for(log)
    lock_dir.mkdir()
    # Backdate the lock dir well past the staleness threshold (simulating a crashed
    # holder that never released it).
    stale_mtime = 0.0
    os.utime(lock_dir, (stale_mtime, stale_mtime))
    monkeypatch.setattr(mod, "_LOCK_MAX_ATTEMPTS", 5)
    monkeypatch.setattr(mod, "_LOCK_RETRY_SECONDS", 0.001)

    assert append_rotating_jsonl(log, json.dumps({"after": 1}), max_bytes=8) is True
    assert not lock_dir.exists()
    rotated = log.with_name(log.name + ".1")
    assert _lines(rotated) == [json.dumps({"seed": True})]
    assert _lines(log) == [json.dumps({"after": 1})]
