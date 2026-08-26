"""CLI composition-seam proof: `dadaia bugs append` threads the SAME operator denylist
source the push-time scan consumes into write-time redaction (SPEC v0.4.5 FR6,
T-045-19).

Intent: CONTRACT — SPEC v0.4.5 FR6/A6.2. Proves the REAL wiring
``cli/commands/bugs.py`` -> ``container.load_denylist_terms()`` ->
``features.bugs.service.BugService`` -> ``core.models.bugs.BugEvent.redact()`` — not a
fake terms list threaded only at the unit-test layer
(``tests/unit/features/bugs/test_write_time_denylist_redaction.py``). Patches the
``container.load_denylist_terms`` composition-root seam directly, mirroring
``tests/contract/test_push_gate_wiring.py``'s own precedent, rather than relying on
``DADAIA_PRIVACY_DENYLIST``/filesystem discovery — this sandbox's own real workspace
can carry an ambient operator denylist file that would make a file/env-based test
nondeterministic.

Size: SMALL (directory-tiered ``integration`` — ``CliRunner`` + tmp filesystem, no
subprocess/network).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    s = tmp_path / "specs"
    (s / "bugs").mkdir(parents=True)
    return s


def _append_leaky(specs_dir: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "bugs",
            "append",
            "--specs-dir",
            str(specs_dir),
            "--bug-id",
            "leaky-cli-denylist",
            "--event",
            "reported",
            "--title",
            "title",
            "--severity",
            "HIGH",
            "--surface",
            "gate",
            "--component",
            "spec_context",
            "--context",
            "dadaia-workspace",
            "--symptom",
            "sym",
            "--repro",
            "repro",
            "--expected",
            "exp",
            "--notes",
            "deployment landed at acme-corp's staging box",
        ],
    )
    assert result.exit_code == 0, result.output


def test_bugs_append_masks_a_denylisted_term_via_the_container_seam(
    specs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE end-to-end RED test (A6.1/A6.2): with the container seam wired to a real
    operator denylist term, ``dadaia bugs append`` must never write the raw term to
    ``bugs.jsonl`` — before the fix, the CLI never even read the loader for this
    command, so the raw term landed on disk unmasked."""
    monkeypatch.setattr(
        container,
        "load_denylist_terms",
        lambda: (("acme-corp", "private client name"),),
    )

    _append_leaky(specs)

    written = (specs / "bugs" / "bugs.jsonl").read_text(encoding="utf-8")
    record = json.loads(written.strip().splitlines()[-1])
    assert "acme-corp" not in record["notes"].lower()
    assert "[REDACTED-TERM]" in record["notes"]


def test_bugs_append_with_empty_denylist_leaves_notes_untouched(
    specs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A6.3 sibling guarantee: with an empty operator denylist (the common case — no
    ``.dadaia/states/privacy_denylist.json``), ``dadaia bugs append`` behaves exactly
    as before FR6 — only IP/home-path masking runs."""
    monkeypatch.setattr(container, "load_denylist_terms", lambda: ())

    _append_leaky(specs)

    written = (specs / "bugs" / "bugs.jsonl").read_text(encoding="utf-8")
    record = json.loads(written.strip().splitlines()[-1])
    assert record["notes"] == "deployment landed at acme-corp's staging box"
