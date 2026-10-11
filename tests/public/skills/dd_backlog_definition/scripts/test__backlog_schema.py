"""sa-backlog-status-has-no-single-authority#B7: no law or skill names
the `picked` status or `**Consumes:**` — the pick is the SPEC's `**Origin:** backlog:`
line. Size: SMALL.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.infrastructure.ledger_scripts import load_owner
from tests.helpers.skill_scripts import stage_skill_scripts

_PUBLIC = Path(dadaia_workspace.__file__).resolve().parent / "public"


def test_no_law_or_skill_names_the_picked_status_or_consumes() -> None:
    pattern = re.compile(r"status: picked|`picked`|\*\*Consumes:\*\*")
    hits = [
        f"{p.relative_to(_PUBLIC)}:{n}"
        for p in _PUBLIC.rglob("*.md")
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if pattern.search(line)
    ]
    assert hits == []


# --- J1.T9 (rc-14, AC13.1): one slug grammar ---------------------------------------------
#
# Seam for J1.T8/T10: the schema is read through the owner's own loader,
# `load_owner("dd-bug-resolution", "_ledger")` -> `load_schema("backlog-v1")` and `validate`,
# never a `public/schemas` path, so T8's move to `dd-backlog-definition/scripts/schemas/`
# (and T11's loader update) leaves this file untouched. `backlog.py new` runs staged.
#
# Bug `slug-grammar-four-patterns-disagree`: `new`, the entry id and `relates` must agree.
# `status` is a live-stage token with its own grammar, not a slug place.
# Which slugs are valid is T10's decision; this file pins only that every place agrees.

_SLUGS = ("a--b", "x", "a-", "9a")


def _entry(**over: object) -> dict[str, object]:
    base = {"id": "ok-slug", "title": "t", "opened": "2026-10-11", "status": "idea"}
    return {**base, "description": "d", "provenance": "p", **over}


def _schema_accepts(entry: dict[str, object]) -> bool:
    ledger = load_owner("dd-bug-resolution", "_ledger")
    schema = ledger.load_schema("backlog-v1")
    document = {"schema": "backlog-v1", "active": [entry]}
    return not list(ledger.validate(document, schema, schema, "document"))


def _new_accepts(tmp_path: Path, slug: str) -> bool:
    for owner in ("dd-release-implementation", "dd-bug-resolution"):
        stage_skill_scripts(owner, tmp_path / "skills" / owner / "scripts")
    script = stage_skill_scripts("dd-backlog-definition", tmp_path / "skills" / "bd" / "scripts")
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps({"schema": "backlog-v1", "active": []}), encoding="utf-8"
    )
    done = subprocess.run(
        [sys.executable, "-B", str(script / "backlog.py"), "new", slug, "--specs", str(specs)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return done.returncode == 0


@pytest.mark.parametrize("slug", _SLUGS)
def test_every_place_a_slug_is_read_gives_the_same_verdict(slug: str, tmp_path: Path) -> None:
    verdicts = {
        "new": _new_accepts(tmp_path, slug),
        "id": _schema_accepts(_entry(id=slug)),
        "relates": _schema_accepts(_entry(relates=[slug])),
    }
    assert len(set(verdicts.values())) == 1, verdicts


def test_the_slug_places_are_one_defs_slug() -> None:
    schema = load_owner("dd-bug-resolution", "_ledger").load_schema("backlog-v1")
    item = schema["$defs"]["activeItem"]["properties"]
    refs = {"id": item["id"], "relates": item["relates"]["items"]}
    assert "slug" in schema["$defs"]
    assert {k: v.get("$ref") for k, v in refs.items()} == dict.fromkeys(refs, "#/$defs/slug")
