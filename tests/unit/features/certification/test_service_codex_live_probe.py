"""codex-live-probe boundary — certify() exercises the INSTALLED Codex, not statics.

Intent: CONTRACT — v0.4.3 A22.4; codex-live-probe-gate-checks-presence-not-usability (an
installed-but-unentitled Codex is the same honest SKIP as an absent one);
certify-skip-detail-leaks-full-codex-output (CWE-532: SKIP/FAIL detail carries only the parsed
upstream message, length-capped — never the banner's workdir/session id, never a raw blob).

A FAKE ``CertificationProcess`` answers; the live probe is
tests/integration/features/certification/test_codex_live_probe_live.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.certification.service import (
    CertificationCheck,
    _all_checks_ok,
    _CertificationSkip,
    _codex_live_probe_detail,
)
from dadaia_workspace.infrastructure.certification_process import CertificationProcessResult


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


# codex-live-probe-gate-checks-presence-not-usability (MEDIUM, reported 2026-08-23):
# an installed-but-unentitled Codex account rejects `codex exec` with an upstream
# invalid_request_error/4xx — that is the SAME "installed Codex is unusable" condition
# `_CertificationSkip` already exists for (see the absent-binary test above), not a new
# state. This fixture reproduces the stderr shape captured on the reporting machine
# (`codex login status` -> "Logged in using ChatGPT", no Codex entitlement) — it
# carries no account identifiers; the operator-local `workdir:` absolute path is
# redacted (never a tracked-file literal, per `.dadaia/AGENTS.md`) and the `session id:` line
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


_WORKDIR = "/fake/sentinel/workdir-9f3c"
_SESSION = "sentinel-session-id-77aa"
_BANNER = (
    f"OpenAI Codex v0.999.0\n--------\nworkdir: {_WORKDIR}\nsession id: {_SESSION}\n--------\n"
)
_SERVER_ERROR = (
    _BANNER
    + 'ERROR: {"type":"error","status":500,"error":{"type":"server_error","message":"upstream internal error, please retry"}}\n'
)
_V = CertificationProcessResult(0, "codex-cli 0.147.0\n", "")
_SKIP = _CertificationSkip


def _exec(code: int, stdout: str = "", stderr: str = "") -> dict[str, CertificationProcessResult]:
    return {"--version": _V, "exec": CertificationProcessResult(code, stdout, stderr)}


# fmt: off
@pytest.mark.parametrize(("which", "responses", "raises", "in_detail"), [
    pytest.param(None, {}, _SKIP, [], id="absent-binary-skips-never-shelled"),
    pytest.param("/usr/bin/codex", {"--version": CertificationProcessResult(1, "", "boom")}, RuntimeError, ["codex --version exited 1"], id="version-exit-fails"),
    pytest.param("/usr/bin/codex", _exec(1, stderr="denied"), RuntimeError, ["codex exec exited 1"], id="exec-exit-fails"),
    pytest.param("/usr/bin/codex", _exec(1, stderr=_REAL_ENTITLEMENT_REJECTION_STDERR), _SKIP,
                 ["installed but unusable", "not supported when using Codex with a ChatGPT account"], id="unentitled-codex-skips-honestly"),
    pytest.param("/usr/bin/codex", _exec(0, "not the marker"), RuntimeError, ["did not echo the expected marker"], id="marker-absent-fails"),
    pytest.param("/usr/bin/codex", _exec(1, stderr=_BANNER + "Error: not logged in. Run `codex login` first.\n"), _SKIP, ["not logged in"], id="CWE-532-not-logged-in-skip-redacted"),
    pytest.param("/usr/bin/codex", _exec(1, stderr=_SERVER_ERROR), RuntimeError, ["upstream internal error, please retry"], id="CWE-532-genuine-failure-parsed-message-only"),
    pytest.param("/usr/bin/codex", _exec(1, stderr=f"segfault probing {_WORKDIR} session={_SESSION}"), RuntimeError, [], id="CWE-532-no-json-no-raw-blob"),
    pytest.param("/usr/bin/codex", _exec(1, stderr="not logged in - " + "x" * 500), _SKIP, [], id="CWE-532-detail-length-capped"),
])
# fmt: on
def test_codex_live_probe_skips_honestly_when_installed_codex_lacks_entitlement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str | None,
    responses: dict[str, CertificationProcessResult], raises: type[Exception], in_detail: list[str],
) -> None:  # fmt: skip
    monkeypatch.setattr("dadaia_workspace.features.certification.service.shutil.which", lambda name: which)
    fake = _FakeCertificationProcess(responses)
    with pytest.raises(raises) as caught:
        _codex_live_probe_detail(fake, tmp_path, "codex", "codex")
    detail = str(caught.value)
    assert type(caught.value) is raises
    assert all(part.lower() in detail.lower() for part in in_detail)
    assert not [leak for leak in (_WORKDIR, _SESSION, "segfault", "x" * 500) if leak in detail]
    assert len(detail) < 400
    assert which or fake.calls == []


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
    detail = _codex_live_probe_detail(fake, tmp_path, "codex", "codex")
    assert "codex-cli 0.147.0" in detail
    assert "DADAIA-LIVE-PROBE-OK" in detail
    # bounded, non-interactive, sandboxed exec — never a live-write / trusted-git call.
    exec_call = fake.calls[1]
    assert "--sandbox" in exec_call
    assert "read-only" in exec_call
    assert "--skip-git-repo-check" in exec_call


@pytest.mark.parametrize(("status", "ok"), [("SKIP", True), ("FAIL", False)])
def test_all_checks_ok_accepts_only_pass_and_skip(status: str, ok: bool) -> None:
    """A22.4: an honest SKIP (no Codex CLI on this host) never fails certification; a FAIL does."""
    checks = [CertificationCheck("capability-contract", "PASS", "ok"), CertificationCheck("codex-live-probe", status, "d")]
    assert _all_checks_ok(checks) is ok
