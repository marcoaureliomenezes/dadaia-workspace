"""FR9 — one deterministic enforcer for the rules-to-skills map (T-044-15).

Intent: CONTRACT — A9.1, A9.2, A9.4 (SPEC v0.4.4). Size: SMALL (pure JSON/Markdown/
frontmatter reads against the real package tree, no subprocess, no network).

This is the ONE enforcer FR9 mandates, reading the REAL
``dadaia_workspace/public/entities/rules-skills-map.json``, the REAL
``dadaia_workspace/public/data/DADAIA.md`` (the law source, title-anchored — never a
hardcoded copy) and the REAL on-disk skills inventory
(``dadaia_workspace/public/skills/*/SKILL.md``), resolved the same way
``infrastructure/public_assets.py`` resolves ``public/`` (``Path(__file__).parent /
"public"`` from the package root). It replaces ``lint-skill-collisions.py`` (retired,
D4): its ``applyTo``-glob overlap logic and ``DECLARED_OVERLAPS`` data are ported
verbatim below, now reading ``declared_overlaps`` from the map JSON instead of a
hardcoded Python list, and its ``--self-test`` fixtures (a) and (b) are ported as
dedicated tests (A9.4) — see ``test_ported_self_test_a_*`` / ``test_ported_self_test_b_*``.

Six failure modes (FR9), each proven by a real "green at HEAD" test plus a dedicated
mutation fixture that turns the SAME check function red (A9.1/A9.2). Every mutation
fixture mutates an in-memory ``copy.deepcopy`` of the real map or a ``tmp_path`` copy of
skill inventory data — never a repo file.

1. A mapped topic/section does not exist in the law (title-anchored; numbers may shift).
2. A skill on disk maps to no row.
3. A row names a skill that does not exist on disk.
4. Two skills share a topic without a non-empty justification.
5. A ``SKILL.md`` exceeds the declared line ceiling (``skill_md_line_ceiling``, G12).
6. Two non-universal skills have an undeclared ``applyTo`` activation-glob overlap.

FR28 (T-044-56, A28.1) adds a seventh, two-directional check to this SAME enforcer — "no
second enforcer" (D4/D10) applies here too. A skill's model-invocation grant is derived,
never hand-kept: the union of every persona frontmatter's ``skills:`` allowlist
(``dadaia_workspace/public/agents/*.md``), plus the universal-grant mechanism failure
mode 6 already treats specially (``_UNIVERSAL_NAMES`` / an ``applyTo`` in
``_UNIVERSAL_GLOBS``) — a universal skill is implicitly granted to every model and must
never be forced into an explicit per-persona allowlist. Against that derived grant set,
the equivalence holds in BOTH directions with the set of skills whose frontmatter
carries ``disable-model-invocation: true``:

7a. A skill in NO allowlist (and not universally granted) must carry
    ``disable-model-invocation: true``.
7b. A skill carrying ``disable-model-invocation: true`` must be in NO allowlist.
"""

from __future__ import annotations

import copy
import json
import re
from itertools import combinations
from pathlib import Path
from typing import Any

import jsonschema
import pytest

pytestmark = pytest.mark.contract

# Resolved the same way infrastructure/public_assets.py resolves `public/`:
# `Path(__file__).parent.parent / "public"` from inside `dadaia_workspace/infrastructure/`
# is `dadaia_workspace/public`; here we walk up from this test file to the package root.
_PKG_ROOT = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_PUBLIC = _PKG_ROOT / "public"
_MAP_PATH = _PUBLIC / "entities" / "rules-skills-map.json"
_SCHEMA_PATH = _PUBLIC / "schemas" / "rules-skills-map-v1.schema.json"
_LAW_PATH = _PUBLIC / "data" / "DADAIA.md"
_SKILLS_DIR = _PUBLIC / "skills"

_HEADING_RE = re.compile(r"^##\s+\d+\.\s+(.+?)\s*$", re.MULTILINE)
_SECTION_FIELD_RE = re.compile(r"^§\d+\s+(.+)$")

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_APPLYTO_RE = re.compile(r'^applyTo:\s*"?([^"\n]*)"?\s*$', re.MULTILINE)

# Ported verbatim from the retired lint-skill-collisions.py: skills whose activation
# surface is intentionally universal/near-universal — never asserted disjoint.
_UNIVERSAL_GLOBS: frozenset[str] = frozenset({"**"})
_UNIVERSAL_NAMES: frozenset[str] = frozenset({"dd-grill-me"})


# --------------------------------------------------------------------------- #
# Loaders — real inputs, source of truth on disk.
# --------------------------------------------------------------------------- #


def _load_json(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _real_map() -> dict[str, Any]:
    return _load_json(_MAP_PATH)


def _real_schema() -> dict[str, Any]:
    return _load_json(_SCHEMA_PATH)


def _law_section_titles(law_path: Path = _LAW_PATH) -> set[str]:
    """Every '## N. Title' heading's Title text — title-anchored, number ignored."""
    text = law_path.read_text(encoding="utf-8")
    return {m.group(1).strip() for m in _HEADING_RE.finditer(text)}


def _section_title(section_field: str) -> str:
    """Strip a map row's '§N ' prefix, leaving the title to resolve against the law."""
    m = _SECTION_FIELD_RE.match(section_field)
    if m is None:
        raise ValueError(f"section field is not title-anchored ('§N <Title>'): {section_field!r}")
    return m.group(1).strip()


def _skills_on_disk(skills_dir: Path = _SKILLS_DIR) -> set[str]:
    return {p.parent.name for p in skills_dir.glob("*/SKILL.md")}


def _mapped_skills(map_data: dict[str, Any]) -> set[str]:
    return {name for row in map_data["rows"] for name in row["skills"]}


# --------------------------------------------------------------------------- #
# Failure mode 1 — mapped section does not exist in the law.
# --------------------------------------------------------------------------- #


def _find_missing_sections(map_data: dict[str, Any], law_titles: set[str]) -> list[str]:
    violations: list[str] = []
    for row in map_data["rows"]:
        title = _section_title(row["section"])
        if title not in law_titles:
            violations.append(
                f"topic {row['topic']!r}: section {row['section']!r} (title {title!r}) "
                "not found as a '## N. <Title>' heading in the law"
            )
    return violations


# --------------------------------------------------------------------------- #
# Failure modes 2/3 — skill<->row bijection.
# --------------------------------------------------------------------------- #


def _find_unmapped_skills(map_data: dict[str, Any], skills: set[str]) -> list[str]:
    return sorted(skills - _mapped_skills(map_data))


def _find_missing_skills(map_data: dict[str, Any], skills: set[str]) -> list[str]:
    return sorted(_mapped_skills(map_data) - skills)


# --------------------------------------------------------------------------- #
# Failure mode 4 — shared topic without justification.
# --------------------------------------------------------------------------- #


def _find_undeclared_shared_topics(map_data: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for row in map_data["rows"]:
        justification = row.get("justification")
        if len(row["skills"]) > 1 and not (justification or "").strip():
            violations.append(row["topic"])
    return violations


# --------------------------------------------------------------------------- #
# Failure mode 5 — SKILL.md line ceiling (G12).
# --------------------------------------------------------------------------- #


def _find_ceiling_violations(map_data: dict[str, Any], skills_dir: Path) -> list[str]:
    ceiling = map_data["skill_md_line_ceiling"]
    violations: list[str] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        n_lines = len(skill_md.read_text(encoding="utf-8").splitlines())
        if n_lines > ceiling:
            violations.append(f"{skill_md.parent.name}: {n_lines} lines > ceiling {ceiling}")
    return violations


# --------------------------------------------------------------------------- #
# Failure mode 6 — undeclared applyTo activation-glob overlap.
# Ported verbatim from lint-skill-collisions.py (D4): _glob_to_regex, _probe_paths,
# globs_overlap, _parse_skill, collect_stage_skills, find_undeclared_overlaps.
# --------------------------------------------------------------------------- #


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a `**`/`*` path glob into an anchored regex."""
    out: list[str] = []
    i = 0
    while i < len(glob):
        ch = glob[i]
        if glob[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _probe_paths(glob: str) -> list[str]:
    """Instantiate 1+ concrete candidate paths a glob could match."""
    filler_segment = "x"
    filler_tail = "x/y/z"
    concrete = glob.replace("**", filler_tail).replace("*", filler_segment)
    return [concrete]


def _globs_overlap(glob_a: str, glob_b: str) -> bool:
    """True if the two globs could both match at least one concrete path."""
    if glob_a == glob_b:
        return True
    regex_a = _glob_to_regex(glob_a)
    regex_b = _glob_to_regex(glob_b)
    for probe in _probe_paths(glob_a):
        if regex_b.match(probe):
            return True
    return any(regex_a.match(probe) for probe in _probe_paths(glob_b))


def _parse_skill_frontmatter(md_path: Path) -> tuple[str, str] | None:
    """Return (name, applyTo) for a SKILL.md, or None if no frontmatter / no name."""
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return None
    raw = m.group(1)
    name_m = _NAME_RE.search(raw)
    if not name_m:
        return None
    apply_m = _APPLYTO_RE.search(raw)
    apply_to = apply_m.group(1).strip() if apply_m else ""
    return name_m.group(1), apply_to


def _collect_stage_skills(skills_dir: Path) -> list[tuple[str, str]]:
    """Return (name, applyTo) pairs for non-universal, path-claiming stage skills."""
    stage: list[tuple[str, str]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        parsed = _parse_skill_frontmatter(skill_md)
        if parsed is None:
            continue
        name, apply_to = parsed
        if not apply_to:
            continue  # no path claim — nothing to collide over
        if apply_to in _UNIVERSAL_GLOBS or name in _UNIVERSAL_NAMES:
            continue
        stage.append((name, apply_to))
    return stage


def _is_declared_pair(name_a: str, name_b: str, declared_groups: list[frozenset[str]]) -> bool:
    return any({name_a, name_b} <= group for group in declared_groups)


def _find_overlap_pairs(
    stage_skills: list[tuple[str, str]], declared_groups: list[frozenset[str]]
) -> list[tuple[str, str]]:
    """Pure port of the retired script's find_undeclared_overlaps — no I/O."""
    findings: list[tuple[str, str]] = []
    for (name_a, glob_a), (name_b, glob_b) in combinations(stage_skills, 2):
        if not _globs_overlap(glob_a, glob_b):
            continue
        if _is_declared_pair(name_a, name_b, declared_groups):
            continue
        findings.append((name_a, name_b))
    return findings


def _declared_overlap_groups(map_data: dict[str, Any]) -> list[frozenset[str]]:
    return [frozenset(group) for group in map_data.get("declared_overlaps", [])]


def _find_undeclared_activation_overlaps(
    map_data: dict[str, Any], skills_dir: Path
) -> list[tuple[str, str]]:
    stage_skills = _collect_stage_skills(skills_dir)
    declared_groups = _declared_overlap_groups(map_data)
    return _find_overlap_pairs(stage_skills, declared_groups)


# --------------------------------------------------------------------------- #
# Schema contract.
# --------------------------------------------------------------------------- #


def test_map_validates_against_its_own_schema() -> None:
    jsonschema.validate(instance=_real_map(), schema=_real_schema())


# --------------------------------------------------------------------------- #
# Six failure modes — green at HEAD (A9.1).
# --------------------------------------------------------------------------- #


def test_every_mapped_section_exists_in_the_law() -> None:
    violations = _find_missing_sections(_real_map(), _law_section_titles())
    assert violations == [], f"row(s) point at a section absent from the law: {violations}"


def test_every_skill_on_disk_is_mapped() -> None:
    violations = _find_unmapped_skills(_real_map(), _skills_on_disk())
    assert violations == [], f"skill(s) on disk map to no row: {violations}"


def test_every_mapped_skill_exists_on_disk() -> None:
    violations = _find_missing_skills(_real_map(), _skills_on_disk())
    assert violations == [], f"row(s) name a skill absent from disk: {violations}"


def test_shared_topics_carry_a_justification() -> None:
    violations = _find_undeclared_shared_topics(_real_map())
    assert violations == [], f"multi-skill row(s) with no justification: {violations}"


def test_every_skill_md_is_within_the_declared_line_ceiling() -> None:
    violations = _find_ceiling_violations(_real_map(), _SKILLS_DIR)
    assert violations == [], f"SKILL.md(s) over the declared ceiling: {violations}"


def test_no_undeclared_activation_glob_overlap() -> None:
    violations = _find_undeclared_activation_overlaps(_real_map(), _SKILLS_DIR)
    assert violations == [], f"undeclared applyTo overlap(s): {violations}"


# --------------------------------------------------------------------------- #
# Six mutation fixtures — one per failure mode, each proven RED against a mutated
# in-memory copy or tmp_path copy of the real inputs (A9.2). Never mutates a repo file.
# --------------------------------------------------------------------------- #


def test_mutation_fixture_1_missing_section_turns_red() -> None:
    mutated = copy.deepcopy(_real_map())
    mutated["rows"][0]["section"] = "§4 A Section Title That Does Not Exist"
    violations = _find_missing_sections(mutated, _law_section_titles())
    assert violations, "a row pointing at a nonexistent section title must be flagged"


def test_mutation_fixture_2_unmapped_skill_turns_red() -> None:
    mutated_skills = _skills_on_disk() | {"fixture-orphan-skill"}
    violations = _find_unmapped_skills(_real_map(), mutated_skills)
    assert violations == ["fixture-orphan-skill"]


def test_mutation_fixture_3_missing_skill_on_disk_turns_red() -> None:
    mutated = copy.deepcopy(_real_map())
    mutated["rows"][0]["skills"] = ["fixture-nonexistent-skill"]
    violations = _find_missing_skills(mutated, _skills_on_disk())
    assert violations == ["fixture-nonexistent-skill"]


def test_mutation_fixture_4_undeclared_shared_topic_turns_red() -> None:
    mutated = copy.deepcopy(_real_map())
    mutated["rows"][0]["skills"] = ["fixture-skill-a", "fixture-skill-b"]
    mutated["rows"][0]["justification"] = None
    violations = _find_undeclared_shared_topics(mutated)
    assert violations == [mutated["rows"][0]["topic"]]


def test_mutation_fixture_5_skill_md_over_ceiling_turns_red(tmp_path: Path) -> None:
    map_data = _real_map()
    ceiling = map_data["skill_md_line_ceiling"]
    fixture_skills_dir = tmp_path / "skills"
    fixture_skill_dir = fixture_skills_dir / "fixture-oversized-skill"
    fixture_skill_dir.mkdir(parents=True)
    oversized_content = "\n".join(f"line {i}" for i in range(ceiling + 20))
    (fixture_skill_dir / "SKILL.md").write_text(oversized_content, encoding="utf-8")

    violations = _find_ceiling_violations(map_data, fixture_skills_dir)
    assert violations, "an oversized fixture SKILL.md must be flagged"
    assert "fixture-oversized-skill" in violations[0]


def test_mutation_fixture_6_undeclared_activation_overlap_turns_red(tmp_path: Path) -> None:
    map_data = _real_map()  # real declared_overlaps — the fixture pair is not in it
    fixture_skills_dir = tmp_path / "skills"
    for name, apply_to in (
        ("fixture-skill-one", "specs/newthing/**"),
        ("fixture-skill-two", "specs/newthing/**"),
    ):
        skill_dir = fixture_skills_dir / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f'---\nname: {name}\napplyTo: "{apply_to}"\n---\n\nbody\n', encoding="utf-8"
        )

    violations = _find_undeclared_activation_overlaps(map_data, fixture_skills_dir)
    assert violations == [("fixture-skill-one", "fixture-skill-two")]


# --------------------------------------------------------------------------- #
# Ported --self-test fixtures (A9.4) — lint-skill-collisions.py --self-test (a)/(b),
# exercised here against the pure `_find_overlap_pairs` (in-memory, no I/O), matching
# the retired script's own self-test shape exactly.
# --------------------------------------------------------------------------- #


def test_ported_self_test_a_universal_glob_skill_produces_no_finding() -> None:
    """Ported from lint-skill-collisions.py --self-test (a): a `**` skill never fires
    even with an obvious path collision — asserted here on the already-filtered stage
    list, exactly as the retired script's own self-test did."""
    universal_case = [("some-universal", "**"), ("some-stage", "specs/foo/**")]
    stage_only = [pair for pair in universal_case if pair[1] not in _UNIVERSAL_GLOBS]
    violations = _find_overlap_pairs(stage_only, [])
    assert violations == []


def test_ported_self_test_b_undeclared_duplicate_glob_fires() -> None:
    """Ported from lint-skill-collisions.py --self-test (b): a newly introduced
    undeclared duplicate pair does fire."""
    duplicate_case = [
        ("fixture-skill-one", "specs/newthing/**"),
        ("fixture-skill-two", "specs/newthing/**"),
    ]
    violations = _find_overlap_pairs(duplicate_case, [])
    assert violations == [("fixture-skill-one", "fixture-skill-two")]


# --------------------------------------------------------------------------- #
# FR28 (T-044-56, A28.1) — the invocation model, checked in BOTH directions,
# no hand-kept list. The grant set is DERIVED: the union of every persona
# frontmatter's `skills:` allowlist, plus the same universal-grant mechanism
# failure mode 6 already special-cases (`_UNIVERSAL_NAMES` / an `applyTo` in
# `_UNIVERSAL_GLOBS`) — a universal skill is implicitly granted to every model
# and must never be forced into an explicit per-persona allowlist to avoid a
# false "no allowlist" finding.
# --------------------------------------------------------------------------- #

_AGENTS_DIR = _PUBLIC / "agents"

_SKILLS_LIST_RE = re.compile(r"^skills:\s*\n((?:  - .+\n)+)", re.MULTILINE)
_DISABLE_MODEL_INVOCATION_RE = re.compile(
    r"^disable-model-invocation:\s*true\s*$", re.MULTILINE | re.IGNORECASE
)


def _agent_skill_allowlist(agent_md: Path) -> set[str]:
    """Parse one persona frontmatter's `skills:` allowlist — empty set if absent."""
    text = agent_md.read_text(encoding="utf-8")
    fm = _FRONTMATTER_RE.match(text)
    raw = fm.group(1) if fm else ""
    m = _SKILLS_LIST_RE.search(raw)
    if not m:
        return set()
    return {line.strip()[2:].strip() for line in m.group(1).splitlines() if line.strip()}


def _persona_skill_grants(agents_dir: Path) -> set[str]:
    """Union of every persona's `skills:` allowlist — derived, never hand-kept."""
    granted: set[str] = set()
    for agent_md in sorted(agents_dir.glob("*.md")):
        granted |= _agent_skill_allowlist(agent_md)
    return granted


def _universal_grant_skills(skills_dir: Path) -> set[str]:
    """Skills failure-mode-6's own filter already treats as universally available —
    `_UNIVERSAL_NAMES`, or any skill whose `applyTo` is a universal glob
    (`_UNIVERSAL_GLOBS`, ported verbatim from the retired lint script). These are
    implicitly granted to every model without appearing in any explicit allowlist."""
    universal: set[str] = set()
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        parsed = _parse_skill_frontmatter(skill_md)
        if parsed is None:
            continue
        name, apply_to = parsed
        if name in _UNIVERSAL_NAMES or apply_to in _UNIVERSAL_GLOBS:
            universal.add(name)
    return universal


def _granted_to_any_model(agents_dir: Path, skills_dir: Path) -> set[str]:
    """The complete model-invocation grant surface (A28.1): explicit allowlists plus
    the universal-grant mechanism."""
    return _persona_skill_grants(agents_dir) | _universal_grant_skills(skills_dir)


def _disable_model_invocation_flagged(skills_dir: Path) -> set[str]:
    """Skills whose frontmatter carries `disable-model-invocation: true`."""
    flagged: set[str] = set()
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        fm = _FRONTMATTER_RE.match(text)
        raw = fm.group(1) if fm else ""
        if _DISABLE_MODEL_INVOCATION_RE.search(raw):
            flagged.add(skill_md.parent.name)
    return flagged


def _find_ungranted_not_flagged(
    skills: set[str], granted: set[str], flagged: set[str]
) -> list[str]:
    """Direction 7a — a skill in NO allowlist (and not universally granted) must carry
    `disable-model-invocation: true`."""
    return sorted(s for s in skills if s not in granted and s not in flagged)


def _find_flagged_but_granted(granted: set[str], flagged: set[str]) -> list[str]:
    """Direction 7b — a skill carrying `disable-model-invocation: true` must be in NO
    allowlist — a model-granted skill can never also claim to be user-invoked-only."""
    return sorted(s for s in flagged if s in granted)


def test_ungranted_skills_carry_disable_model_invocation() -> None:
    """Direction 7a (A28.1) — a skill no persona's `skills:` allowlist grants to a
    model, and that is not universally granted (failure mode 6's own exemption), must
    carry `disable-model-invocation: true`."""
    granted = _granted_to_any_model(_AGENTS_DIR, _SKILLS_DIR)
    flagged = _disable_model_invocation_flagged(_SKILLS_DIR)
    violations = _find_ungranted_not_flagged(_skills_on_disk(), granted, flagged)
    assert violations == [], (
        f"skill(s) granted by no persona allowlist and not universally granted, but "
        f"missing disable-model-invocation: true: {violations}"
    )


def test_disable_model_invocation_skills_are_in_no_allowlist() -> None:
    """Direction 7b (A28.1) — a skill flagged `disable-model-invocation: true` must be
    in NO persona's `skills:` allowlist — the equivalence holds both ways, not as a
    one-way rule."""
    granted = _granted_to_any_model(_AGENTS_DIR, _SKILLS_DIR)
    flagged = _disable_model_invocation_flagged(_SKILLS_DIR)
    violations = _find_flagged_but_granted(granted, flagged)
    assert violations == [], (
        f"skill(s) flagged disable-model-invocation: true but still granted by a "
        f"persona allowlist (contradicts A28.1's user-invoked-only meaning): {violations}"
    )


# --------------------------------------------------------------------------- #
# Two mutation fixtures — one per direction (7a/7b), each proven RED against an
# in-memory mutated grant/flag set built from the real skill/agent inventory.
# Never mutates a repo file.
# --------------------------------------------------------------------------- #


def test_mutation_fixture_7_ungranted_skill_without_flag_turns_red() -> None:
    """Direction 7a mutation fixture: drop a real, explicitly-allowlisted (non-
    universal) skill out of the granted set without flagging it — the finder must
    catch it."""
    target = "dd-cli-library"
    granted = _granted_to_any_model(_AGENTS_DIR, _SKILLS_DIR)
    assert target in granted, "fixture precondition: target must start out granted"
    mutated_granted = granted - {target}
    flagged = _disable_model_invocation_flagged(_SKILLS_DIR)
    assert target not in flagged, "fixture precondition: target must start out unflagged"

    violations = _find_ungranted_not_flagged(_skills_on_disk(), mutated_granted, flagged)
    assert violations == [target]


def test_mutation_fixture_8_flagged_skill_still_granted_turns_red() -> None:
    """Direction 7b mutation fixture: flag a real, currently-granted skill as
    disable-model-invocation without removing it from any allowlist — the finder must
    catch the contradiction."""
    target = "dev-server-registry"
    granted = _granted_to_any_model(_AGENTS_DIR, _SKILLS_DIR)
    assert target in granted, "fixture precondition: target must start out granted"
    mutated_flagged = {target}

    violations = _find_flagged_but_granted(granted, mutated_flagged)
    assert violations == [target]
