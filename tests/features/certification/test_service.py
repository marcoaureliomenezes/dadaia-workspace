"""`certify` over a real journey: its `dadaia` and `git` children run for real.

T-050-50; 0.4.7 FR4/T-047-16 (every verb certify shells exists: its
check PASSes). Size: MEDIUM — only `init` (a venv build) and harness binaries are faked.

codex-live-probe boundary — certify() exercises the INSTALLED Codex, not statics.

v0.4.3 A22.4; codex-live-probe-gate-checks-presence-not-usability (an
installed-but-unentitled Codex is the same honest SKIP as an absent one);
certify-skip-detail-leaks-full-codex-output (CWE-532: SKIP/FAIL detail carries only the parsed
upstream message, length-capped — never the banner's workdir/session id, never a raw blob).

A FAKE ``CertificationProcess`` answers; the live probe runs only under ``dadaia certify``.

Per-record live probes — one `<harness>-live-probe` for every registered record.

`dadaia certify` probes the INSTALLED runtime of every harness the registry knows, by
iteration and never by a hand-written line per harness. The probe carries NO version
floor: the workspace derives the same four behaviours into every harness and pins no
release of any of them. An absent binary leaves the runtime claim UNVERIFIED — an honest,
non-failing degrade — while an installed binary that cannot answer is a genuine failure.

These tests inject a FAKE process and a fake `PATH` lookup; no real binary is touched.
"""

from __future__ import annotations

import json
import os
import site
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.features.certification import service
from dadaia_workspace.features.certification.service import (
    _HARNESS_PROBE_BINARIES,
    CertificationCheck,
    _all_checks_ok,
    _CertificationSkip,
    _codex_live_probe_detail,
    _version_probe_detail,
    certify,
)
from dadaia_workspace.infrastructure.certification_process import (
    CertificationProcessResult,
    SubprocessCertificationProcess,
)
from tests.fixtures.stores import own_venv_python, own_venv_workspace


class _Children(SubprocessCertificationProcess):
    """`init` lays a workspace plus slop; `dadaia` runs on *python*, `git` for real."""

    def __init__(self, python: Path) -> None:
        self._python = str(python)

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CertificationProcessResult:
        if argv[0] not in ("git", sys.executable):
            return CertificationProcessResult(1, "", "not exercised")
        if list(argv[3:4]) == ["init"]:
            (own_venv_workspace(Path(argv[4])) / ".dadaia" / "nonsense").mkdir()
            (Path(argv[4]) / "notes.txt").write_text("operator notes", encoding="utf-8")
            return CertificationProcessResult(0, "", "")
        path = os.pathsep.join([str((env or {}).get("PYTHONPATH")), *site.getsitepackages()])
        argv = [self._python if argv[0] == sys.executable else argv[0], *argv[1:]]
        return super().run(argv, cwd=cwd, env={**(env or {}), "PYTHONPATH": path}, timeout=timeout)


@pytest.mark.medium
@pytest.mark.slow(reason="a real certify journey: about a dozen dadaia children")
def test_certify_fails_naming_the_sandbox_slop(tmp_path: Path) -> None:
    """sa-reconcile-certify-skip-the-workspace-walk#B1: a certify sandbox seeded with
    `.dadaia/nonsense/` and a root `notes.txt` — the workspace section is judged and the
    result fails naming WS-dadaia-slop and WS-root-slop. sa-certify-children-resolve-the-
    live-workspace: run from a "live" workspace owning the children's venv, every child
    acts on the sandbox only — the live registry is byte-identical, no session is left."""
    live = own_venv_workspace(tmp_path / "live")
    result = certify(live, _Children(own_venv_python(live))).to_dict()

    assert (live / ".dadaia" / "states" / "spec_contexts.json").read_bytes() == b'{"contexts": []}'
    assert sorted(p.name for p in (live / ".dadaia").iterdir()) == [".venv", "states", "tmp"]
    checks = {c["name"]: c for c in result["checks"] if not c["name"].endswith("-probe")}
    failed = {name for name, c in checks.items() if c["status"] != "PASS"}
    assert result["ok"] is False
    assert failed == {"specs-scaffold-and-doctor", "context-specs-doctor"}, json.dumps(
        {n: checks[n]["detail"] for n in failed}, indent=1
    )
    for name in failed:
        assert {"WS-dadaia-slop", "WS-root-slop"} <= set(checks[name]["detail"].split())


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


class _FakeProcess:
    """The ``CertificationProcess`` protocol's ``run`` only — a version probe never
    starts a long-running process."""

    def __init__(self, result: CertificationProcessResult) -> None:
        self._result = result
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
        return self._result

    def start(self, argv: list[str], *, cwd: Path, env: dict[str, str]) -> object:
        raise AssertionError("a live probe never starts a long-running process")


def _result(returncode: int = 0, stdout: str = "", stderr: str = "") -> CertificationProcessResult:
    return CertificationProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)


def test_every_registered_record_has_a_probe_binary() -> None:
    """A record with no binary would silently never be probed."""
    assert set(_HARNESS_PROBE_BINARIES) == set(L1_ENTRY_HARNESSES)


@pytest.mark.parametrize("harness", sorted(_HARNESS_PROBE_BINARIES))
def test_the_probe_leaves_the_claim_unverified_when_the_binary_is_absent(
    harness: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one behaviour the task pins: no binary on PATH degrades honestly, naming the
    claim UNVERIFIED and never running anything."""
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    fake = _FakeProcess(_result())

    with pytest.raises(_CertificationSkip) as excinfo:
        _version_probe_detail(fake, tmp_path, harness, _HARNESS_PROBE_BINARIES[harness])

    message = str(excinfo.value)
    assert message.startswith("UNVERIFIED:"), message
    assert _HARNESS_PROBE_BINARIES[harness] in message
    assert harness in message
    assert fake.calls == [], "an absent binary must not be executed"


@pytest.mark.parametrize(
    ("result", "outcome"),
    [
        pytest.param(_result(stdout="cursor-agent 0.0.1-alpha\n"), "cursor-agent 0.0.1-alpha", id="answers-passes-with-no-version-floor"),
        pytest.param(_result(returncode=3, stderr="cursor: panic"), RuntimeError("cursor: panic"), id="present-but-broken-is-a-genuine-failure"),
    ],
)  # fmt: skip
def test_an_installed_binary_passes_by_answering_and_fails_only_if_it_cannot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: CertificationProcessResult,
    outcome: str | Exception,
) -> None:
    """Only ABSENCE is an honest degrade; the version is reported as evidence, never compared to a floor."""
    monkeypatch.setattr(service.shutil, "which", lambda name: f"/opt/bin/{name}")
    fake = _FakeProcess(result)
    if isinstance(outcome, Exception):
        with pytest.raises(RuntimeError, match=str(outcome)):
            _version_probe_detail(fake, tmp_path, "cursor", "cursor-agent")
    else:
        assert outcome in _version_probe_detail(fake, tmp_path, "cursor", "cursor-agent")
    assert fake.calls == [["/opt/bin/cursor-agent", "--version"]]
