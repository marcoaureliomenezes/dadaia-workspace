"""Per-record live probes — one `<harness>-live-probe` for every registered record.

Intent: CONTRACT — 0.4.7 FR3 / T-047-76; size: SMALL (unit).

`dadaia certify` probes the INSTALLED runtime of every harness the registry knows, by
iteration and never by a hand-written line per harness. The probe carries NO version
floor: the workspace derives the same four behaviours into every harness and pins no
release of any of them. An absent binary leaves the runtime claim UNVERIFIED — an honest,
non-failing degrade — while an installed binary that cannot answer is a genuine failure.

These tests inject a FAKE process and a fake `PATH` lookup; no real binary is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.features.certification import service
from dadaia_workspace.features.certification.service import (
    _HARNESS_PROBE_BINARIES,
    _CertificationSkip,
    _version_probe_detail,
)
from dadaia_workspace.infrastructure.certification_process import CertificationProcessResult


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
