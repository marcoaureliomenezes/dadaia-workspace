"""A handoff's `context` is the context NAME, not the repo directory slug.

`dadaia context create <name> --repo <slug>` accepts a name that differs from the repo
slug — there is a dedicated test for that shape. But `self_pull` ref resolution joined
`repos/<context>/<ref>` literally, so a compliant handoff citing the canonical context
name failed validation, and only passed if the author substituted the slug — a different
string, and not the one the schema documents for that field
(bug `b1-r01-self-pull-context-name-vs-repo-slug`).

Found by the consumer-side validator during a real audit dispatch, reproduced twice.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.reports.validation import ReportsValidationService
from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator

_SCHEMA = (
    Path(__file__).resolve().parents[4]
    / "dadaia_workspace"
    / "public"
    / "schemas"
    / "handoff-v1.schema.json"
)


def _service(ws: Path) -> ReportsValidationService:
    """Built the way the container builds it — with the real slug resolver injected."""
    from dadaia_workspace.core.specs_resolver import repo_slug_for_context

    return ReportsValidationService(
        StdlibHandoffValidator(_SCHEMA),
        ws / ".dadaia" / "reports",
        slug_resolver=repo_slug_for_context,
    )


def _workspace(tmp_path: Path, *, context: str, slug: str) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "contexts": [
                    {"name": context, "state": "alive", "repo_slug": slug, "repo_url": ""}
                ],
            }
        ),
        encoding="utf-8",
    )
    atom = tmp_path / "repos" / slug / "specs" / "memory" / "quality-assurance.md"
    atom.parent.mkdir(parents=True)
    atom.write_text("# qa\n", encoding="utf-8")
    return tmp_path


def _handoff(tmp_path: Path, context: str) -> Path:
    path = tmp_path / ".dadaia" / "handoff" / "h.handoff.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "handoff-v1.2",
                "agent": "qa-engineer",
                "context": context,
                "produced_at": "2026-08-03T00:00:00Z",
                "scope": "s",
                "metrics": {},
                "self_pull": {"refs": ["specs/memory/quality-assurance.md"]},
                "artifact": {"type": "other"},
                "findings": [],
                "verdict": "APPROVED",
                "next_handoff": {
                    "agent": "human",
                    "context": context,
                    "expected_artifact_type": "other",
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_a_context_name_that_differs_from_the_repo_slug_resolves(tmp_path: Path) -> None:
    ws = _workspace(tmp_path, context="dadaia-workspace", slug="dw-repo")

    errors = _service(ws).validate_file(_handoff(ws, "dadaia-workspace")).errors

    assert [e for e in errors if "self_pull" in e.field_path] == [], [
        (e.field_path, e.message) for e in errors
    ]


def test_a_ref_that_exists_nowhere_is_still_rejected(tmp_path: Path) -> None:
    """The guard must not become permissive — a bogus ref still fails."""
    ws = _workspace(tmp_path, context="dadaia-workspace", slug="dw-repo")
    path = _handoff(ws, "dadaia-workspace")
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["self_pull"]["refs"] = ["specs/memory/does-not-exist.md"]
    path.write_text(json.dumps(doc), encoding="utf-8")

    errors = _service(ws).validate_file(path).errors

    assert [e for e in errors if "self_pull" in e.field_path], "a missing ref must still fail"
