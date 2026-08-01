"""Unit tests for SpecsDoctor SPEC-DOC-033 — event-sourced JSONL bug-telemetry invariant.

Release v0.1.46 / T-46-04 (AC-1). Covers per-line schema validity, the rotation ceiling,
and event coherence over the terminal set {resolved, superseded, deferred, rejected}.

Bug-stream coherence (SPEC-DOC-033) guards the event-sourced ledger — the cross-file
chronological-ordering test is kept as a named test (a reported in an earlier file makes
a terminal in a later file coherent, proving the check reads files in ts order, not
lexical file order).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue


def _bugs_dir(specs: Path) -> Path:
    d = specs / "bugs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _reported(
    bug_id: str, *, severity: str = "HIGH", ts: str = "2026-07-01T13:00:00Z"
) -> dict[str, Any]:
    return {
        "bug_id": bug_id,
        "event": "reported",
        "ts": ts,
        "reported_by": "software-engineer",
        "title": f"title {bug_id}",
        "severity": severity,
        "surface": "gate",
        "component": "spec_context",
        "context": "dadaia-workspace",
        "tags": ["gate"],
        "symptom": "sym",
        "repro": "repro",
        "expected": "exp",
        "notes": "n",
    }


def _resolved(bug_id: str, *, ts: str = "2026-07-01T14:00:00Z") -> dict[str, Any]:
    return {
        "bug_id": bug_id,
        "event": "resolved",
        "ts": ts,
        "reported_by": "software-engineer",
        "release": "v0.1.46",
    }


def _write_log(bugs: Path, name: str, events: list[dict[str, Any]]) -> Path:
    path = bugs / name
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def _doc033(specs: Path) -> list[SpecsDoctorIssue]:
    return [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-033"]


def test_coherence_spans_multiple_files_in_chronological_order(tmp_path: Path) -> None:
    """A reported in an earlier file makes a terminal in a later file coherent."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(bugs, "20260701T13Z-00.jsonl", [_reported("bug-a")])
    _write_log(bugs, "20260701T14Z-00.jsonl", [_resolved("bug-a")])
    assert _doc033(specs) == []


# ---------------------------------------------------------------------------
# Violation rows — terminal-without-reported, double-terminal, malformed,
# schema-fail (x2), over-ceiling — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("build", "expect_description_contains"),
    [
        pytest.param(
            lambda bugs: _write_log(bugs, "20260701T13Z-00.jsonl", [_resolved("orphan")]),
            "no 'reported' event anywhere",
            id="terminal-without-any-reported",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs,
                "20260701T13Z-00.jsonl",
                [
                    _reported("bug-a"),
                    _resolved("bug-a"),
                    _resolved("bug-a", ts="2026-07-01T16:00:00Z"),
                ],
            ),
            "second terminal event",
            id="double-terminal",
            marks=pytest.mark.skip(
                reason="reclassificado: um segundo terminal é uma CORREÇÃO que supersede "
                "(WARNING), coberto por test_a_correcting_terminal_warns_but_does_not_error"
            ),
        ),
        pytest.param(
            lambda bugs: (bugs / "20260701T13Z-00.jsonl").write_text(
                "{not json\n", encoding="utf-8"
            ),
            "not valid JSON",
            id="malformed-json-line",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs,
                "20260701T13Z-00.jsonl",
                [
                    {
                        "bug_id": "b",
                        "event": "reported",
                        "ts": "2026-07-01T13:00:00Z",
                        "reported_by": "se",
                        "title": "only a title",
                    }
                ],
            ),
            "schema",
            id="reported-missing-required-payload-fails-schema",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs,
                "20260701T13Z-00.jsonl",
                [
                    {
                        "bug_id": "b",
                        "event": "exploded",
                        "ts": "2026-07-01T13:00:00Z",
                        "reported_by": "se",
                    }
                ],
            ),
            "schema",
            id="bad-event-enum-fails-schema",
        ),
        pytest.param(
            lambda bugs: _write_log(
                bugs, "20260701T13Z-00.jsonl", [_reported(f"b{i}") for i in range(1001)]
            ),
            "rotation ceiling",
            id="over-ceiling-1001-rows",
        ),
    ],
)
def test_violation_matrix(tmp_path: Path, build, expect_description_contains: str) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    build(bugs)
    errors = _doc033(specs)
    matching = [e for e in errors if expect_description_contains in e.description]
    assert matching, f"Expected an error containing {expect_description_contains!r}, got: {errors}"
    assert all(e.severity is Severity.ERROR for e in matching)


# ---------------------------------------------------------------------------
# Clean rows — noop/negative-control/archived-exempt/at-ceiling — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda specs: None, id="no-bugs-dir-noop"),
        pytest.param(
            lambda specs: _write_log(
                _bugs_dir(specs), "20260701T13Z-00.jsonl", [_reported("bug-a"), _resolved("bug-a")]
            ),
            id="coherent-reported-then-resolved-negative-control",
        ),
        pytest.param(
            lambda specs: _write_log(
                _bugs_dir(specs),
                "20260701T13Z-00.jsonl",
                [
                    _reported("bug-a"),
                    _resolved("bug-a"),
                    {
                        "bug_id": "bug-a",
                        "event": "archived",
                        "ts": "2026-07-01T15:00:00Z",
                        "reported_by": "project-auditor",
                    },
                ],
            ),
            id="archived-after-resolved-exempt",
        ),
        pytest.param(
            lambda specs: _write_log(
                _bugs_dir(specs), "20260701T13Z-00.jsonl", [_reported(f"b{i}") for i in range(1000)]
            ),
            id="exactly-at-ceiling-clean",
        ),
    ],
)
def test_clean_matrix(tmp_path: Path, build) -> None:  # type: ignore[no-untyped-def]
    specs = tmp_path / "specs"
    specs.mkdir(exist_ok=True)
    build(specs)
    assert _doc033(specs) == []


def test_a_correcting_terminal_warns_but_does_not_error(tmp_path: Path) -> None:
    """Um ledger append-only tem de conseguir registar «aquela disposição estava errada».

    A regra `bug-registration-guardrail` diz que uma disposição feita por engano se corrige
    acrescentando a certa a seguir, com o motivo a dizê-lo — o fold fica com a última.
    Proibir isso empurrava a correção para fora do rasto de evidência, que é o único sítio
    onde ela não pode acontecer. Fica WARNING para continuar visível.
    """
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(
        bugs,
        "20260701T13Z-00.jsonl",
        [
            _reported("bug-a"),
            _resolved("bug-a", ts="2026-07-01T15:00:00Z"),
            _resolved("bug-a", ts="2026-07-01T16:00:00Z"),
        ],
    )

    issues = _doc033(specs)
    second = [i for i in issues if "second terminal" in i.description]

    assert second, f"a correção tem de continuar visível, não silenciosa: {issues}"
    assert all(i.severity is Severity.WARNING for i in second)
    assert not [i for i in issues if i.severity is Severity.ERROR], (
        "corrigir uma disposição não pode reprovar a árvore inteira"
    )


def test_a_terminal_with_no_reported_is_still_an_error(tmp_path: Path) -> None:
    """A tolerância acima não pode abrir a porta ao defeito que o SPEC-DOC-033 existe para apanhar."""
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(bugs, "20260701T13Z-00.jsonl", [_resolved("orphan-bug")])

    errors = [i for i in _doc033(specs) if i.severity is Severity.ERROR]

    assert errors, "fechar um bug que ninguém abriu continua a ser um erro"


def test_a_reconstructed_opening_appended_late_warns_but_does_not_error(tmp_path: Path) -> None:
    """Um log append-only não consegue inserir a abertura ANTES de um terminal já escrito.

    Doze bugs foram fechados por um agente que só acrescentou o terminal, antes de o guard
    r19 existir; verificado em 163 revisões de git, o `reported` nunca existiu. A reparação
    honesta num ledger append-only é um lançamento compensatório, que por construção fica
    depois. O invariante que importa é «nenhum bug foi fechado sem nunca ter sido aberto» —
    uma abertura tardia é a reparação, não o defeito.
    """
    specs = tmp_path / "specs"
    bugs = _bugs_dir(specs)
    _write_log(
        bugs,
        "20260701T13Z-00.jsonl",
        [
            _resolved("bug-a", ts="2026-07-01T15:00:00Z"),
            _reported("bug-a", ts="2026-07-01T15:00:00Z"),
        ],
    )

    issues = _doc033(specs)

    assert not [i for i in issues if i.severity is Severity.ERROR], (
        f"uma abertura reconstruída não pode reprovar a árvore: {issues}"
    )
    late = [i for i in issues if "precedes its 'reported'" in i.description]
    assert late and all(i.severity is Severity.WARNING for i in late), (
        "a reparação tem de continuar visível, nunca silenciosa"
    )
