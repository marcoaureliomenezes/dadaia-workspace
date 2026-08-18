"""Unit tests for WS-CDX-PROTOCOL doctor checks (T-30-B-01 / T-30-B-02; v0.4.3 T-043-34).

Intent: CONTRACT — v0.4.3 A22.3

check_codex_rule_corpus_reachable (A6): proves every by-name rule cited in a
Codex-projected agent artifact resolves to a reachable on-disk surface at
.claude/rules/<name>.md. STATIC reference integrity only (the file exists) — a
different claim from ``codex_trust_boundary_info``'s effective prompt visibility.

codex_trust_boundary_info (A7/A22.3): emits a VERSION-QUALIFIED INFO line built from
a runtime ``codex --version`` probe (injectable via ``version_probe`` for these unit
tests) — degrading honestly, with no unqualified hook-fire claim, whenever Codex is
absent or the installed version was never live-certified.

All fixtures are synthesized under tmp_path — no real projection is read. The
version-probe tests inject a fake probe (never the real installed binary) — a live
Codex exec is `certification/service.py`'s job (A22.4), not this doctor check's.
"""

from __future__ import annotations

import inspect
import pathlib
import subprocess

import pytest

from dadaia_workspace.infrastructure import codex_doctor
from dadaia_workspace.infrastructure.codex_doctor import (
    _CODEX_HOOKS_LIVE_CERTIFIED_VERSION,
    _probe_installed_codex_version,
    check_codex_rule_corpus_reachable,
    codex_trust_boundary_info,
)


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


def _make_codex_agent(workspace: pathlib.Path, name: str, body: str) -> None:
    agents = workspace / ".codex" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{name}.toml").write_text(
        f'name = "{name}"\ndeveloper_instructions = """\n{body}\n"""\n',
        encoding="utf-8",
    )


def _make_rule(workspace: pathlib.Path, name: str) -> None:
    rules = workspace / ".claude" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")


@pytest.mark.parametrize(
    "case",
    [
        "all-reachable-ok",
        "unreachable-reports-error",
        "no-citations-silent",
        "no-codex-dir-silent",
        "unreachable-name-deduped",
    ],
)
def test_rule_corpus_reachable(tmp_path: pathlib.Path, case: str) -> None:
    if case == "all-reachable-ok":
        _make_codex_agent(
            tmp_path,
            "software-engineer",
            "Follow the `workspace-protocol` rule and the `release-governance` rule.",
        )
        _make_rule(tmp_path, "workspace-protocol")
        _make_rule(tmp_path, "release-governance")

        out = _rendered(check_codex_rule_corpus_reachable(tmp_path))
        assert out == ["[ok] codex:rule-corpus-reachable (WS-CDX-PROTOCOL)"]

    elif case == "unreachable-reports-error":
        _make_codex_agent(
            tmp_path,
            "software-engineer",
            "See the `workspace-protocol` rule and the `nonexistent-rule` rule.",
        )
        _make_rule(tmp_path, "workspace-protocol")
        # nonexistent-rule.md deliberately absent.

        out = _rendered(check_codex_rule_corpus_reachable(tmp_path))
        assert len(out) == 1
        assert "nonexistent-rule" in out[0]
        assert out[0].startswith("[error] codex:rule-corpus")
        assert "WS-CDX-PROTOCOL" in out[0]

    elif case == "no-citations-silent":
        _make_codex_agent(tmp_path, "lonely", "No rules referenced here.")
        assert check_codex_rule_corpus_reachable(tmp_path) == []

    elif case == "no-codex-dir-silent":
        assert check_codex_rule_corpus_reachable(tmp_path) == []

    else:  # unreachable-name-deduped
        _make_codex_agent(tmp_path, "a", "Use the `missing-rule` rule.")
        _make_codex_agent(tmp_path, "b", "Also the `missing-rule` rule.")

        out = _rendered(check_codex_rule_corpus_reachable(tmp_path))
        assert len(out) == 1
        assert "missing-rule" in out[0]


def test_trust_boundary_info_degrades_honestly_when_codex_absent() -> None:
    """A22.3: no installed Codex CLI observed ⇒ honest degrade, no unqualified claim."""
    out = _rendered(codex_trust_boundary_info(version_probe=lambda: None))

    assert len(out) == 1
    line = out[0]
    assert line.startswith("[info] codex:trust-boundary")
    assert "UNVERIFIED" in line
    assert "hooks fire and block" not in line
    assert "never fire" not in line
    assert "WS-CDX-HYGIENE" in line


def test_trust_boundary_info_certified_version_states_fire_in_both() -> None:
    """A22.3: the exact live-certified version states the fire-in-both fact, version-qualified."""
    out = _rendered(
        codex_trust_boundary_info(version_probe=lambda: _CODEX_HOOKS_LIVE_CERTIFIED_VERSION)
    )

    assert len(out) == 1
    line = out[0]
    assert line.startswith("[info] codex:trust-boundary")
    assert _CODEX_HOOKS_LIVE_CERTIFIED_VERSION in line
    assert "fire and block" in line
    assert "BOTH" in line
    assert "TUI" in line
    assert "headless" in line
    assert "WS-CDX-HYGIENE" in line


def test_trust_boundary_info_uncertified_version_degrades_honestly() -> None:
    """A22.3: an installed version other than the last live-certified one never asserts
    the fire-in-both claim — it names the observed version and points at the live
    re-certification mechanism (`dadaia certify`, A22.4) instead of guessing."""
    out = _rendered(codex_trust_boundary_info(version_probe=lambda: "codex-cli 0.147.0"))

    assert len(out) == 1
    line = out[0]
    assert line.startswith("[info] codex:trust-boundary")
    assert "codex-cli 0.147.0" in line
    assert "UNVERIFIED" in line
    assert "dadaia certify" in line
    assert "fire and block" not in line
    assert "WS-CDX-HYGIENE" in line


def test_trust_boundary_info_default_wiring_uses_the_real_probe() -> None:
    """The zero-arg call (production wiring in public_assets.py) must use the real
    runtime probe, not a test seam left disconnected."""
    sig = inspect.signature(codex_trust_boundary_info)
    assert sig.parameters["version_probe"].default is _probe_installed_codex_version


def test_probe_installed_codex_version_absent_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_doctor.shutil, "which", lambda name: None)
    assert _probe_installed_codex_version() is None


def test_probe_installed_codex_version_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_doctor.shutil, "which", lambda name: "/usr/bin/codex")

    def _fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

    monkeypatch.setattr(codex_doctor.subprocess, "run", _fake_run)
    assert _probe_installed_codex_version() is None


def test_probe_installed_codex_version_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_doctor.shutil, "which", lambda name: "/usr/bin/codex")

    def _fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="codex --version", timeout=5)

    monkeypatch.setattr(codex_doctor.subprocess, "run", _fake_run)
    assert _probe_installed_codex_version() is None


def test_probe_installed_codex_version_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_doctor.shutil, "which", lambda name: "/usr/bin/codex")

    def _fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="codex-cli 0.147.0\n", stderr="")

    monkeypatch.setattr(codex_doctor.subprocess, "run", _fake_run)
    assert _probe_installed_codex_version() == "codex-cli 0.147.0"
