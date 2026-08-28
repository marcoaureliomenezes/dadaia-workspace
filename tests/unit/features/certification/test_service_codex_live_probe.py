"""codex-live-probe boundary — certify() exercises the INSTALLED Codex, not statics.

Intent: CONTRACT — v0.4.3 A22.4

Static Codex projection tests validate SHAPE only (files exist, TOML parses); they
never attest runtime behavior. ``_codex_live_probe_detail`` is the one place
certification actually runs a live ``codex exec`` — bounded timeout, honest
``_CertificationSkip`` (never FAIL) when no ``codex`` binary is reachable. These unit
tests inject a FAKE ``CertificationProcess`` and never touch a real binary; a live
integration test that runs when Codex is actually installed lives at
tests/integration/features/certification/test_codex_live_probe_live.py (T-043-34,
env-gated with a declared plan ref).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.certification_process import CertificationProcessResult
from dadaia_workspace.features.certification.service import (
    CertificationCheck,
    _all_checks_ok,
    _CertificationSkip,
    _codex_live_probe_detail,
)


class _FakeCertificationProcess:
    """Implements the ``CertificationProcess`` protocol's ``run`` only — the codex-live
    -probe boundary never calls ``start`` (no long-running process involved)."""

    def __init__(self, responses: dict[str, CertificationProcessResult]) -> None:
        self._responses = responses
        self.calls: list[list[str]] = []

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        timeout: float,
    ) -> CertificationProcessResult:
        self.calls.append(list(argv))
        key = argv[1] if len(argv) > 1 else argv[0]
        return self._responses[key]

    def start(self, argv: list[str], *, cwd: Path, env: dict[str, str]) -> object:
        raise NotImplementedError("codex-live-probe never starts a background process")


def test_codex_live_probe_skips_honestly_when_codex_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which", lambda name: None
    )
    fake = _FakeCertificationProcess({})
    with pytest.raises(_CertificationSkip):
        _codex_live_probe_detail(fake, tmp_path)
    assert fake.calls == [], "an absent binary must never be shelled out to"


def test_codex_live_probe_fails_on_nonzero_version_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    fake = _FakeCertificationProcess({"--version": CertificationProcessResult(1, "", "boom")})
    with pytest.raises(RuntimeError, match="codex --version exited 1"):
        _codex_live_probe_detail(fake, tmp_path)


def test_codex_live_probe_fails_on_nonzero_exec_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    fake = _FakeCertificationProcess(
        {
            "--version": CertificationProcessResult(0, "codex-cli 0.147.0\n", ""),
            "exec": CertificationProcessResult(1, "", "denied"),
        }
    )
    with pytest.raises(RuntimeError, match="codex exec exited 1"):
        _codex_live_probe_detail(fake, tmp_path)


# codex-live-probe-gate-checks-presence-not-usability (MEDIUM, reported 2026-08-23):
# an installed-but-unentitled Codex account rejects `codex exec` with an upstream
# invalid_request_error/4xx — that is the SAME "installed Codex is unusable" condition
# `_CertificationSkip` already exists for (see the absent-binary test above), not a new
# state. This fixture reproduces the stderr shape captured on the reporting machine
# (`codex login status` -> "Logged in using ChatGPT", no Codex entitlement) — it
# carries no account identifiers; the operator-local `workdir:` absolute path is
# redacted (never a tracked-file literal, per DADAIA.md §8) and the `session id:` line
# is a synthetic placeholder UUID (codex-probe-unit-fixture-carries-real-session-uuid),
# both inert to the classifier under test (it parses the trailing `ERROR: {...}` JSON
# payload, not either of these lines).
_REAL_ENTITLEMENT_REJECTION_STDERR = (
    "Reading additional input from stdin...\n"
    "OpenAI Codex v0.145.0\n"
    "--------\n"
    "workdir: [REDACTED-LOCAL-PATH]\n"
    "model: gpt-5.6-sol\n"
    "provider: openai\n"
    "approval: never\n"
    "sandbox: read-only\n"
    "reasoning effort: high\n"
    "reasoning summaries: none\n"
    "session id: deadbeef-dead-4bee-8bee-deadbeefdead\n"
    "--------\n"
    "user\n"
    "Reply with exactly the single line: DADAIA-LIVE-PROBE-OK. No tool calls, no other "
    "text.\n"
    "warning: Model metadata for `gpt-5.6-sol` not found. Defaulting to fallback "
    "metadata; this can degrade performance and cause issues.\n"
    'ERROR: {"type":"error","status":400,"error":{"type":"invalid_request_error",'
    '"message":"The \'gpt-5.6-sol\' model is not supported when using Codex with a '
    'ChatGPT account."}}\n'
    'ERROR: {"type":"error","status":400,"error":{"type":"invalid_request_error",'
    '"message":"The \'gpt-5.6-sol\' model is not supported when using Codex with a '
    'ChatGPT account."}}\n'
)


def test_codex_live_probe_skips_honestly_when_installed_codex_lacks_entitlement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """codex-live-probe-gate-checks-presence-not-usability: installed-but-unusable
    Codex (upstream 4xx invalid_request_error, e.g. no model entitlement on the signed
    -in account) is an honest environment degrade, not a probe defect — same
    ``_CertificationSkip`` classification as an absent binary, consumed identically by
    both ``certify()``'s ``check()`` wrapper and the live integration test's dynamic
    skip."""
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    fake = _FakeCertificationProcess(
        {
            "--version": CertificationProcessResult(0, "codex-cli 0.145.0\n", ""),
            "exec": CertificationProcessResult(1, "", _REAL_ENTITLEMENT_REJECTION_STDERR),
        }
    )
    with pytest.raises(_CertificationSkip, match="installed but unusable") as excinfo:
        _codex_live_probe_detail(fake, tmp_path)
    assert "not supported when using Codex with a ChatGPT account" in str(excinfo.value)


def test_codex_live_probe_fails_when_marker_absent_from_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    fake = _FakeCertificationProcess(
        {
            "--version": CertificationProcessResult(0, "codex-cli 0.147.0\n", ""),
            "exec": CertificationProcessResult(0, "not the marker", ""),
        }
    )
    with pytest.raises(RuntimeError, match="did not echo the expected marker"):
        _codex_live_probe_detail(fake, tmp_path)


def test_codex_live_probe_passes_and_reports_version_and_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    fake = _FakeCertificationProcess(
        {
            "--version": CertificationProcessResult(0, "codex-cli 0.147.0\n", ""),
            "exec": CertificationProcessResult(0, "DADAIA-LIVE-PROBE-OK\n", ""),
        }
    )
    detail = _codex_live_probe_detail(fake, tmp_path)
    assert "codex-cli 0.147.0" in detail
    assert "DADAIA-LIVE-PROBE-OK" in detail
    # bounded, non-interactive, sandboxed exec — never a live-write / trusted-git call.
    exec_call = fake.calls[1]
    assert "--sandbox" in exec_call
    assert "read-only" in exec_call
    assert "--skip-git-repo-check" in exec_call


def test_all_checks_ok_treats_skip_as_a_non_failing_outcome() -> None:
    """A22.4: an honest SKIP (e.g. no Codex CLI on this host) must never fail
    certification — only PASS/SKIP are acceptable outcomes, FAIL is not."""
    checks = [
        CertificationCheck("capability-contract", "PASS", "ok"),
        CertificationCheck("codex-live-probe", "SKIP", "codex CLI not found on PATH"),
    ]
    assert _all_checks_ok(checks) is True


def test_all_checks_ok_still_fails_on_a_real_failure() -> None:
    checks = [
        CertificationCheck("capability-contract", "PASS", "ok"),
        CertificationCheck("codex-live-probe", "FAIL", "codex exec exited 1: denied"),
    ]
    assert _all_checks_ok(checks) is False
