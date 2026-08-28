"""codex-live-probe SKIP/FAIL detail redaction seam (CWE-532).

Intent: CONTRACT — certify-skip-detail-leaks-full-codex-output

``certify-skip-detail-leaks-full-codex-output`` (LOW, CWE-532): the classifier seam
(``_codex_environment_unavailable_reason`` / the ``codex exec`` failure branch of
``_codex_live_probe_detail``) used to embed the WHOLE captured ``codex exec``
output — including the upstream banner's ``workdir:`` and ``session id:`` lines —
into the ``detail`` field ``certify --json`` renders, on both the SKIP (not-logged-in/
not-authenticated refusal) branch and the genuine FAIL branch. This suite proves the
fixed seam carries only the parsed upstream ``error.message`` (or an explicit
refusal/byte-count marker when none is parseable), length-capped, routed through the
workspace's existing masking primitive (``core.redaction.Redactor``) — never the raw
blob. Fake fixtures below use recognizable SENTINEL workdir/session-id values (never
real local paths) so a leak is unambiguous, exactly as the fixture already established
in ``test_service_codex_live_probe.py`` for the real-world entitlement-rejection case
this suite extends.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.certification_process import CertificationProcessResult
from dadaia_workspace.features.certification.service import (
    _CertificationSkip,
    _codex_live_probe_detail,
)


class _FakeCertificationProcess:
    """Implements the ``CertificationProcess`` protocol's ``run`` only — mirrors the
    fixture in ``test_service_codex_live_probe.py`` (kept local rather than imported
    cross-file: this directory has no ``__init__.py`` package marker)."""

    def __init__(self, responses: dict[str, CertificationProcessResult]) -> None:
        self._responses = responses

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        timeout: float,
    ) -> CertificationProcessResult:
        key = argv[1] if len(argv) > 1 else argv[0]
        return self._responses[key]

    def start(self, argv: list[str], *, cwd: Path, env: dict[str, str]) -> object:
        raise NotImplementedError("codex-live-probe never starts a background process")


_SENTINEL_WORKDIR = "/fake/sentinel/workdir-9f3c"
_SENTINEL_SESSION_ID = "sentinel-session-id-77aa"

_FAKE_NOT_LOGGED_IN_STDERR = (
    "OpenAI Codex v0.999.0\n"
    "--------\n"
    f"workdir: {_SENTINEL_WORKDIR}\n"
    "model: gpt-9\n"
    "provider: openai\n"
    f"session id: {_SENTINEL_SESSION_ID}\n"
    "--------\n"
    "user\n"
    "Reply with exactly the single line: DADAIA-LIVE-PROBE-OK. No tool calls, no other "
    "text.\n"
    "Error: not logged in. Run `codex login` first.\n"
)

_FAKE_GENUINE_FAILURE_STDERR = (
    "OpenAI Codex v0.999.0\n"
    "--------\n"
    f"workdir: {_SENTINEL_WORKDIR}\n"
    f"session id: {_SENTINEL_SESSION_ID}\n"
    "--------\n"
    'ERROR: {"type":"error","status":500,"error":{"type":"server_error",'
    '"message":"upstream internal error, please retry"}}\n'
)


def _fake_process(exec_stderr: str) -> _FakeCertificationProcess:
    return _FakeCertificationProcess(
        {
            "--version": CertificationProcessResult(0, "codex-cli 0.999.0\n", ""),
            "exec": CertificationProcessResult(1, "", exec_stderr),
        }
    )


def test_skip_detail_never_leaks_workdir_or_session_id_on_not_logged_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    with pytest.raises(_CertificationSkip) as excinfo:
        _codex_live_probe_detail(_fake_process(_FAKE_NOT_LOGGED_IN_STDERR), tmp_path)
    detail = str(excinfo.value)
    assert _SENTINEL_WORKDIR not in detail
    assert _SENTINEL_SESSION_ID not in detail
    assert "not logged in" in detail.lower()


def test_fail_detail_never_leaks_workdir_or_session_id_on_genuine_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    with pytest.raises(RuntimeError) as excinfo:
        _codex_live_probe_detail(_fake_process(_FAKE_GENUINE_FAILURE_STDERR), tmp_path)
    detail = str(excinfo.value)
    assert _SENTINEL_WORKDIR not in detail
    assert _SENTINEL_SESSION_ID not in detail
    assert "upstream internal error, please retry" in detail


def test_fail_detail_never_leaks_raw_output_when_no_json_error_is_parseable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash with no ``ERROR: {...}`` JSON at all must still never embed the raw
    blob — there is no legitimate parsed message to show, so the detail must fall
    back to a non-content marker rather than any captured byte."""
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    raw_crash = f"segfault while probing {_SENTINEL_WORKDIR} session={_SENTINEL_SESSION_ID}"
    with pytest.raises(RuntimeError) as excinfo:
        _codex_live_probe_detail(_fake_process(raw_crash), tmp_path)
    detail = str(excinfo.value)
    assert _SENTINEL_WORKDIR not in detail
    assert _SENTINEL_SESSION_ID not in detail
    assert "segfault" not in detail


def test_skip_detail_is_length_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "dadaia_workspace.features.certification.service.shutil.which",
        lambda name: "/usr/bin/codex",
    )
    long_line = "not logged in - " + ("x" * 500)
    with pytest.raises(_CertificationSkip) as excinfo:
        _codex_live_probe_detail(_fake_process(long_line), tmp_path)
    detail = str(excinfo.value)
    assert "x" * 500 not in detail
    assert len(detail) < 400
