"""M-1 rider (v0.4.3 T-043-50 six-axis review) — ``dadaia ci gc-push-verdicts`` CLI wiring.

Intent: CONTRACT — M-1 (six-axis review finding, T-043-50)

FR24's ``gc_consumed_push_verdicts`` (``features/chokepoints/service.py``, T-043-39) had
no production caller: this file proves the thin CLI wrapper the ship flow now invokes
immediately after a successful ``git push`` of ``develop``. The exhaustive lane/AG.1/
ledger behavior is proven at the service level in
``tests/unit/features/chokepoints/test_push_verdict_gc.py`` — this file does not
re-derive it; it proves arg parsing, wiring (via monkeypatch injection), output shape and
exit codes, plus one real-filesystem round trip so the wiring is not mocked all the way
down.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app as main_app
from dadaia_workspace.features.chokepoints import GcOutcome

runner = CliRunner()

_SHA_A = "a" * 40
_SHA_B = "b" * 40


def _patch_repo(monkeypatch: pytest.MonkeyPatch, ws: Path) -> None:
    """Same pattern as ``test_cli_ci.py``: stub the repo/workspace resolution seam."""
    monkeypatch.setattr(ci, "_repo_root", lambda: ws)
    monkeypatch.setattr(ci, "_resolve_workspace_root", lambda repo_root: ws)


def _write_handoff(
    path: Path,
    *,
    agent: str = "security-reviewer",
    verdict: str | None = "APPROVED",
    commit_sha: str | None = _SHA_A,
) -> None:
    payload: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": agent,
        "context": "demo-ctx",
        "produced_at": "2026-06-12T12:00:00Z",
        "artifact": {"type": "other"},
    }
    metrics: dict[str, object] = {}
    if commit_sha is not None:
        metrics["commit_sha"] = commit_sha
    payload["metrics"] = metrics
    if verdict is not None:
        payload["verdict"] = verdict
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------


def test_missing_sha_is_a_usage_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_repo(monkeypatch, tmp_path)

    result = runner.invoke(main_app, ["ci", "gc-push-verdicts"])

    assert result.exit_code != 0


def test_help_documents_the_cadence_contract() -> None:
    """The reviewer-required documented caller: --help states WHEN this runs."""
    result = runner.invoke(main_app, ["ci", "gc-push-verdicts", "--help"])

    assert result.exit_code == 0
    lowered = result.stdout.lower()
    assert "ship flow" in lowered
    assert "git push" in lowered
    assert "develop" in lowered
    assert "tip" in lowered


# ---------------------------------------------------------------------------
# Wiring — via monkeypatch injection (no real filesystem GC)
# ---------------------------------------------------------------------------


def test_wires_the_resolved_workspace_and_sha_set_into_the_service_function(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo(monkeypatch, tmp_path)
    captured: dict[str, object] = {}

    def fake_gc(workspace_root: Path, pushed_shas: object, **_kwargs: object) -> GcOutcome:
        captured["workspace_root"] = workspace_root
        captured["pushed_shas"] = set(pushed_shas)  # type: ignore[call-overload]
        return GcOutcome()

    monkeypatch.setattr(ci, "gc_consumed_push_verdicts", fake_gc)

    result = runner.invoke(main_app, ["ci", "gc-push-verdicts", "--sha", _SHA_A, "--sha", _SHA_B])

    assert result.exit_code == 0
    assert captured["workspace_root"] == tmp_path
    assert captured["pushed_shas"] == {_SHA_A, _SHA_B}


def test_reports_consumed_and_skipped_counts_and_ledger_basename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo(monkeypatch, tmp_path)
    monkeypatch.setattr(
        ci,
        "gc_consumed_push_verdicts",
        lambda *a, **k: GcOutcome(
            deleted=("sec-approve-a.handoff.json",),
            ledgered=("sec-approve-a.handoff.json",),
            append_failed=("sec-approve-b.handoff.json",),
            lane_guard_refused=("sec-approve-c.handoff.json",),
        ),
    )

    result = runner.invoke(main_app, ["ci", "gc-push-verdicts", "--sha", _SHA_A])

    assert result.exit_code == 0
    assert "consumed 1" in result.stdout
    assert "skipped 2" in result.stdout
    assert "push-verdict-gc-ledger.jsonl" in result.stdout
    assert "sec-approve-a.handoff.json" in result.stdout
    assert "sec-approve-b.handoff.json" in result.stdout
    assert "sec-approve-c.handoff.json" in result.stdout


def test_no_match_still_exits_zero_never_a_failure_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A29.3-style contract mirrored for FR24: idempotent, best-effort, never a failing
    exit code a caller could misread as a push problem."""
    _patch_repo(monkeypatch, tmp_path)
    monkeypatch.setattr(ci, "gc_consumed_push_verdicts", lambda *a, **k: GcOutcome())

    result = runner.invoke(main_app, ["ci", "gc-push-verdicts", "--sha", _SHA_A])

    assert result.exit_code == 0
    assert "consumed 0" in result.stdout
    assert "skipped 0" in result.stdout


def test_dry_run_never_calls_the_deleting_service_function(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo(monkeypatch, tmp_path)

    def _boom(*_a: object, **_k: object) -> GcOutcome:
        raise AssertionError("gc_consumed_push_verdicts must never run under --dry-run")

    monkeypatch.setattr(ci, "gc_consumed_push_verdicts", _boom)
    monkeypatch.setattr(
        ci,
        "iter_security_approvals",
        lambda handoff_root: [
            _FakeApproval(commit_sha=_SHA_A, source="sec-approve-a.handoff.json"),
            _FakeApproval(commit_sha=_SHA_B, source="sec-approve-b.handoff.json"),
        ],
    )

    result = runner.invoke(main_app, ["ci", "gc-push-verdicts", "--sha", _SHA_A, "--dry-run"])

    assert result.exit_code == 0
    assert "would consume 1" in result.stdout
    assert "sec-approve-a.handoff.json" in result.stdout
    assert "sec-approve-b.handoff.json" not in result.stdout


class _FakeApproval:
    def __init__(self, *, commit_sha: str, source: str) -> None:
        self.commit_sha = commit_sha
        self.source = source


# ---------------------------------------------------------------------------
# Real filesystem round trip — the wiring is not mocked all the way down.
# ---------------------------------------------------------------------------


def test_real_run_deletes_the_matching_handoff_and_writes_the_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_repo(monkeypatch, tmp_path)
    ctx_dir = tmp_path / ".dadaia" / "handoff" / "demo-ctx"
    matching = ctx_dir / "sec-approve-a.handoff.json"
    unrelated = ctx_dir / "sec-approve-b.handoff.json"
    _write_handoff(matching, commit_sha=_SHA_A)
    _write_handoff(unrelated, commit_sha=_SHA_B)

    result = runner.invoke(main_app, ["ci", "gc-push-verdicts", "--sha", _SHA_A])

    assert result.exit_code == 0
    assert not matching.exists()
    assert unrelated.exists()
    ledger = tmp_path / ".dadaia" / "logs" / "push-verdict-gc-ledger.jsonl"
    assert ledger.exists()
    line = json.loads(ledger.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert line["commit_sha"] == _SHA_A


def test_real_dry_run_deletes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_repo(monkeypatch, tmp_path)
    ctx_dir = tmp_path / ".dadaia" / "handoff" / "demo-ctx"
    matching = ctx_dir / "sec-approve-a.handoff.json"
    _write_handoff(matching, commit_sha=_SHA_A)

    result = runner.invoke(main_app, ["ci", "gc-push-verdicts", "--sha", _SHA_A, "--dry-run"])

    assert result.exit_code == 0
    assert matching.exists()
    ledger = tmp_path / ".dadaia" / "logs" / "push-verdict-gc-ledger.jsonl"
    assert not ledger.exists()
