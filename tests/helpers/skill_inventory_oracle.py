"""One derived skill-inventory oracle (v0.4.5 FR4, ``coupled-inventory-shared-oracle``).

Before this module, three places each kept their OWN idea of "the set of skills":
``tests/e2e/features/test_public_pipeline.py``'s hand-typed ``EXPECTED_SKILLS`` literal,
a hand-kept single-skill path assertion in ``tests/integration/test_public_assets.py``,
and ``tests/scripts/check_skill_orphans.py``'s own independent
``{d.name for d in skills_dir.iterdir() if d.is_dir()}`` scan. Inside v0.4.4 alone that
coupled-but-separately-maintained trio produced two bugs: a skill added/renamed/removed
in the real tree and forgotten in one of the three copies.

This module is the single, DERIVED source of that inventory: it reuses
:func:`tests.helpers.public_asset_roster.scan` — itself a thin wrapper over
``FileSystemPublicAssetManager``'s own private walk (``_iter_files`` /
``_is_ignored_public_asset``, the EXACT enumeration ``install()``/``stage()``/
``doctor()`` use internally) — and extracts the top-level directory name under
``skills/`` from every real (non-ignored) file path already enumerated there.

A skill, product-side, IS "a directory under ``dadaia_workspace/public/skills/``" — the
same definition ``dadaia_workspace/infrastructure/codex_doctor.check_agent_skill_refs``
uses via ``(skills_dir / skill).is_dir()``. Deriving the name set from the roster's
already-proven file enumeration (rather than re-walking ``skills/`` a second,
independently-maintained time) keeps this oracle coupled to the ONE real walk instead of
adding a fourth scan that could itself drift from the other three.

**FR10A re-measurement (v0.5.0, T-050-19A).** T-050-19 (FR10) landed a second,
independent glob — ``tests/contract/test_behavior_map.py``'s ``_skills_on_disk``/
``_scoped_agents_md_sources`` — covering skills AND scoped ``AGENTS.md`` sources for the
behavior-map enforcer. FR10A's scope is deletion-only: retire every remaining
``EXPECTED_SKILLS``-style hand-kept roster either glob already makes redundant.
Re-measured at task time against the exact command the SPEC names (``grep -rn`` for the
three alternatives ``EXPECTED_SKILLS``, ``SKILL_ROSTER``, ``frozenset({`` under ``tests/``,
restricted to skill/persona/``AGENTS.md`` membership): the three literals this module's own opening
paragraph names as retired by v0.4.5 FR4 stay retired — zero-hit grep for a live
``EXPECTED_SKILLS =`` assignment anywhere in the tree — and all four bugs this oracle
exists to prevent a recurrence of (``skill-orphans-unwired-agent-frontmatter``,
``test-public-assets-stale-grill-me-name``, ``test-public-pipeline-stale-skill-roster``,
``skill-orphan-checker-misses-disable-model-invocation``) carry ``status: resolved`` in
``specs/bugs/BUGS.jsonl``. No further skill/persona/``AGENTS.md``-membership roster
survives in ``tests/`` for either glob to replace: this module remains the ONE consumer
every skill-roster reader in the repo goes through, and FR10's ``_scoped_agents_md_sources``
has no pre-existing hand-kept consumer to retire — it is net-new discovery, not a
replacement. The full raw-grep disposition table (every hit, kept-or-repointed, with a
reason) is T-050-19A's task evidence in ``specs/releases/0.5.0/TASKS.md``.
"""

from __future__ import annotations

from pathlib import Path

from tests.helpers.public_asset_roster import default_public_dir, scan

_SKILLS_PREFIX = "skills/"


def skill_names(public_dir: Path | None = None) -> set[str]:
    """The exact set of skill directory names under ``public/skills/``.

    Derived from :func:`tests.helpers.public_asset_roster.scan`'s real file
    enumeration — never a hand-kept list. Defaults to the real package's
    ``dadaia_workspace/public/`` tree; a caller exercising a mutated COPY of
    ``public/`` (never the real tree) passes that copy's ``public/`` root explicitly,
    exactly as :func:`tests.helpers.public_asset_roster.scan` does.
    """
    root = public_dir if public_dir is not None else default_public_dir()
    names: set[str] = set()
    for rel in scan(root):
        if not rel.startswith(_SKILLS_PREFIX):
            continue
        name = rel[len(_SKILLS_PREFIX) :].split("/", 1)[0]
        if name:
            names.add(name)
    return names
