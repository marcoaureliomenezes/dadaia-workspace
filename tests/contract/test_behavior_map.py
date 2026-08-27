"""D14/FR10 — one deterministic enforcer for the behavior map (T-050-19).

Intent: CONTRACT — A10.1-A10.6 (SPEC v0.5.0). Size: SMALL (pure JSON/Markdown/
frontmatter reads against the real package tree, no subprocess, no network).

This file **retires and extends** `tests/contract/test_rules_skills_map.py` (FR9,
v0.4.4) — "no second enforcer" (D4/D10): one map file
(`dadaia_workspace/public/entities/behavior-map.json`), one schema
(`dadaia_workspace/public/schemas/behavior-map-v1.schema.json`), one enforcer module.
`rules-skills-map.json` and its schema are retired in the SAME commit (A10.3, zero-hit
grep for the old filename outside history). The full accounting of what ported, what
folded into a broader check, and what is structurally obviated — proven by a
**name-diff with a zero-hit residue** (A10.6) — is recorded in
`specs/releases/0.5.0/reviews/T-050-19-enforcer-name-diff.md`, produced BEFORE the old
file was deleted; this docstring does not repeat it.

**What D14 adds over FR9's `rules-skills-map.json`.** The old schema modelled a row as
`{topic, section, skills: [...], justification}` — N skills sharing ONE row. The new
schema models a row as `{section, anchor, skill, scoped_agents_md: [...], hash_tuple,
recorded_by, recorded_at}` — cardinality moves from "N skills per topic-row" to
"exactly one row per member" (A10.1): a member (one skill name, OR the row's
`scoped_agents_md` path set) maps to **exactly one** row/section; a section MAY be
owned by more than one row — unlimited, unlike the old model's "shared topic needs a
justification" guard, which is now structurally impossible to need (see the name-diff's
group-2 note on `test_shared_topics_carry_a_justification`). D14 also adds a member type
the old map never covered at all: every **scoped `AGENTS.md`/`*-AGENTS.md` SOURCE** under
`dadaia_workspace/public/{data,scaffold,templates}/` (never the projected instance
path — see the citation-bug note below), discovered the same structural way the skill
inventory already is: **glob the generators, never a hand-written roster**
(`_skills_on_disk`/`_scoped_agents_md_sources` below). `public/data/AGENTS.md` is
excluded by name — it is, together with `public/data/DADAIA.md`, the LAW SOURCE itself
(the two files `public/data/*.md` law state so), not a scoped rule.

Five NEW RED conditions this map's own completeness requires, each with a dedicated
mutation fixture (A10.2), listed in the name-diff's closing table:

1. A member (skill or scoped `AGENTS.md` source) on disk has no row.
2. A row names a member path that does not exist on disk.
3. The same member maps to more than one row (A10.1's "exactly one" cardinality).
4. A `DADAIA.md` section has zero owning rows (A10.1's "at least one owner" cardinality
   — the OLD enforcer never checked this direction at all).
5. A member's real content hash no longer matches its row's recorded `hash_tuple` entry
   (A10.4 — re-recording a hash is a deliberate, reviewed act).

Every failure message in this module names **what to re-read** — the file/section to
open, never merely "a hash changed" (A10.4's own acceptance line).

**Bug-history citations (A16.2 discipline, applied per fold 3 `qa-engineer` amendment
6).** Two bugs the retired `test_rules_skills_map.py` carried are re-cited here because
this file's own five new mutation fixtures reproduce the exact same fixture SHAPE that
fired both — proving RED on this platform is not sufficient; the fix must be structural,
not observational:

* `citation-enforcer-resolves-projected-instance-paths-against-the-checkout` (HIGH) — a
  citation/reference check resolved a `specs/`-prefixed token against checkout
  PRESENCE, when the token actually named a PROJECTED instance path that a bare CI
  clone never has on disk. This module's `scoped_agents_md` entries are SOURCE paths
  under `dadaia_workspace/public/` for exactly this reason — never the projected
  destination (e.g. `specs/bugs/AGENTS.md`), which would silently repeat this exact bug
  class on the new member type. `test_every_mapped_member_exists_on_disk` and the
  `scoped_agents_md` schema pattern (`^dadaia_workspace/public/`) are the structural
  fix, not a per-row allowlist.
* `citation-mutation-fixtures-never-turn-red-on-windows` (HIGH) — a mutation fixture
  that DETECTED its planted violation correctly but rendered the violation's
  `file:line`-shaped message with the OS-native separator, so a naive string
  comparison in a Windows-specific assertion could pass vacuously. Every violation
  string this module produces is built from POSIX-relative paths
  (`Path.relative_to(...).as_posix()` — never `str(path)`, never
  `os.path.join`-shaped interpolation), and the five new mutation fixtures below build
  their fixture data purely in-memory (`copy.deepcopy` of the real map, or literal
  fabricated strings) — never a real filesystem path whose separator could vary — so
  the RED direction is provable identically on POSIX and Windows CI runners.

FR27 (citation check) and FR28 (bidirectional model-invocation grant check) are ported
verbatim from `test_rules_skills_map.py` below (both are independent of the map's row
shape — they scan `public/**/*.md` broadly and derive the grant set from persona
frontmatter/skill frontmatter). Their own docstrings, preserved from the original file,
document their behaviour and bug citations in full.

**(a) Path citations — FR27, ported verbatim.** A backticked token is *path-shaped*
only if it starts with one of three prefixes that are real, checked-in directories of
THIS repo — ``specs/``, ``dadaia_workspace/``, ``.github/`` — resolved against the repo
root; or it is a *bare* filename (``<name>.md|json|rules|txt``, no ``/``) immediately
annotated ``(sibling)`` / ``sibling`` in the surrounding prose, resolved first against
the citing file's own folder, falling back to anywhere under
``dadaia_workspace/public/``.

**(b) Command citations — FR27, ported verbatim.** A backticked span containing the
standalone word ``dadaia`` followed by up to two further lowercase-hyphen words is the
acceptance line's own ``dadaia <verb> [<sub>]`` shape, resolved against the live
``typer`` command tree (imported, never a subprocess ``--help`` parse).

**FR28 — ported verbatim.** A skill's model-invocation grant is derived, never
hand-kept: the union of every persona frontmatter's ``skills:`` allowlist plus the
universal-grant mechanism (failure mode 6's own ``_UNIVERSAL_NAMES`` /
``_UNIVERSAL_GLOBS``), checked in both directions against
``disable-model-invocation: true``.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import re
import tempfile
from collections import Counter
from itertools import combinations
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any

import jsonschema
import pytest
from typer.main import get_command

from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

# Resolved the same way infrastructure/public_assets.py resolves `public/`: walk up
# from this test file to the package root, same as the retired enforcer.
_PKG_ROOT = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_PUBLIC = _PKG_ROOT / "public"
_MAP_PATH = _PUBLIC / "entities" / "behavior-map.json"
_SCHEMA_PATH = _PUBLIC / "schemas" / "behavior-map-v1.schema.json"
_LAW_PATH = _PUBLIC / "data" / "DADAIA.md"
_SKILLS_DIR = _PUBLIC / "skills"
_REPO_ROOT = _PKG_ROOT.parent

_HEADING_RE = re.compile(r"^##\s+\d+\.\s+(.+?)\s*$", re.MULTILINE)
_SECTION_FIELD_RE = re.compile(r"^§\d+\s+(.+)$")

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_APPLYTO_RE = re.compile(r'^applyTo:\s*"?([^"\n]*)"?\s*$', re.MULTILINE)

# Ported verbatim from the retired lint-skill-collisions.py (via test_rules_skills_map.py):
# skills whose activation surface is intentionally universal/near-universal.
_UNIVERSAL_GLOBS: frozenset[str] = frozenset({"**"})
_UNIVERSAL_NAMES: frozenset[str] = frozenset({"dd-grill-me"})

# --------------------------------------------------------------------------- #
# D14 — scoped AGENTS.md/*-AGENTS.md SOURCE discovery. Structural (glob the
# generators), never a hand-written roster — the exact defect D14 exists to catch
# (this SPEC's own first Draft omitted three sources that ship today).
# --------------------------------------------------------------------------- #

_SCOPED_SUBDIRS = ("data", "scaffold", "templates")
# The law source itself — public/data/*.md carries DADAIA.md + AGENTS.md, the two LAW
# files, never a "scoped" rule — is the ONE exclusion from an otherwise-structural glob.
_LAW_SOURCE_RELPATH = "dadaia_workspace/public/data/AGENTS.md"


# --------------------------------------------------------------------------- #
# FR27/A27.20 — the citation check constants. See the module docstring for the
# full citable-pattern definition and exclusion rules.
# --------------------------------------------------------------------------- #

_CITATION_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER_CHARS = frozenset("<>{}*|")
_ELLIPSIS_MARKERS = ("...", "…")
_WORKSPACE_RUNTIME_PREFIX = ".dadaia/"
_CITABLE_PATH_PREFIXES = ("specs/", "dadaia_workspace/", ".github/")
_SIBLING_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:md|json|rules|txt)$")
_SIBLING_MARKER_RE = re.compile(r"^\(?\s*sibling\b")
_BLOCKQUOTE_PREFIX_RE = re.compile(r"^>\s*")

_DADAIA_VERB_RE = re.compile(
    r"(?<![\w./-])dadaia(?!\w)(?:\s+([a-z][a-z0-9-]*))?(?:\s+([a-z][a-z0-9-]*))?"
)


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


def _law_section_bodies(law_path: Path = _LAW_PATH) -> dict[str, str]:
    """Title -> section body text, from its heading through, exclusive of, the next
    heading — the exact span `hash_tuple.section` hashes (A10.4)."""
    text = law_path.read_text(encoding="utf-8")
    heads = list(_HEADING_RE.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(heads):
        start = m.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out[m.group(1).strip()] = text[start:end]
    return out


def _section_title(section_field: str) -> str:
    """Strip a map row's '§N ' prefix, leaving the title to resolve against the law."""
    m = _SECTION_FIELD_RE.match(section_field)
    if m is None:
        raise ValueError(f"section field is not title-anchored ('§N <Title>'): {section_field!r}")
    return m.group(1).strip()


def _skills_on_disk(skills_dir: Path = _SKILLS_DIR) -> set[str]:
    skills = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    assert_populated(skills, sentinel="dd-cli-library")
    return skills


def _scoped_agents_md_sources(public_dir: Path = _PUBLIC) -> set[str]:
    """Every scoped `AGENTS.md`/`*-AGENTS.md` SOURCE under
    `dadaia_workspace/public/{data,scaffold,templates}/`, repo-relative POSIX,
    excluding the law source itself (`public/data/AGENTS.md`)."""
    found: set[str] = set()
    for sub in _SCOPED_SUBDIRS:
        base = public_dir / sub
        if not base.exists():
            continue
        candidates = set(base.glob("**/AGENTS.md")) | set(base.glob("**/*-AGENTS.md"))
        for p in candidates:
            rel = "dadaia_workspace/public/" + p.relative_to(public_dir).as_posix()
            if rel == _LAW_SOURCE_RELPATH:
                continue
            found.add(rel)
    assert_populated(found, sentinel="dadaia_workspace/public/scaffold/bugs/AGENTS.md")
    return found


def _mapped_skill_names(map_data: dict[str, Any]) -> list[str]:
    return [row["skill"] for row in map_data["rows"] if row["skill"] is not None]


def _mapped_scoped_paths(map_data: dict[str, Any]) -> list[str]:
    return [p for row in map_data["rows"] for p in row["scoped_agents_md"]]


# --------------------------------------------------------------------------- #
# Ported mode 1 — mapped section does not exist in the law.
# --------------------------------------------------------------------------- #


def _find_missing_sections(map_data: dict[str, Any], law_titles: set[str]) -> list[str]:
    violations: list[str] = []
    for row in map_data["rows"]:
        title = _section_title(row["section"])
        if title not in law_titles:
            violations.append(
                f"skill={row['skill']!r}: section {row['section']!r} (title {title!r}) "
                "not found as a '## N. <Title>' heading in the law"
            )
    return violations


# --------------------------------------------------------------------------- #
# D14 — member<->row bijection, generalized over BOTH member types (folds the
# retired modes 2/3 — see the name-diff for the "folded, not dropped" accounting).
# --------------------------------------------------------------------------- #


def _find_unmapped_members(
    map_data: dict[str, Any], skills: set[str], scoped_sources: set[str]
) -> list[str]:
    mapped_skills = set(_mapped_skill_names(map_data))
    mapped_scoped = set(_mapped_scoped_paths(map_data))
    violations = [f"skill:{s}" for s in sorted(skills - mapped_skills)]
    violations += [f"scoped_agents_md:{s}" for s in sorted(scoped_sources - mapped_scoped)]
    return violations


def _find_dangling_member_references(
    map_data: dict[str, Any], skills: set[str], scoped_sources: set[str]
) -> list[str]:
    mapped_skills = set(_mapped_skill_names(map_data))
    mapped_scoped = set(_mapped_scoped_paths(map_data))
    violations = [f"skill:{s}" for s in sorted(mapped_skills - skills)]
    violations += [f"scoped_agents_md:{s}" for s in sorted(mapped_scoped - scoped_sources)]
    return violations


# --------------------------------------------------------------------------- #
# D14/A10.1 — new cardinality checks the old enforcer never had.
# --------------------------------------------------------------------------- #


def _find_members_mapped_to_two_sections(map_data: dict[str, Any]) -> list[str]:
    """A10.1's "exactly one row" direction — a member (skill name, or one
    scoped_agents_md path) claimed by more than one row is a violation regardless of
    whether the two rows happen to name the same section: the ROW is the ownership
    unit, and a member owned by two rows is ambiguous by construction."""
    skill_counts = Counter(_mapped_skill_names(map_data))
    scoped_counts = Counter(_mapped_scoped_paths(map_data))
    violations = [f"skill:{k}" for k, v in sorted(skill_counts.items()) if v > 1]
    violations += [f"scoped_agents_md:{k}" for k, v in sorted(scoped_counts.items()) if v > 1]
    return violations


def _find_sections_without_an_owner(map_data: dict[str, Any], law_titles: set[str]) -> list[str]:
    """A10.1's "at least one owner" direction — a `DADAIA.md` section with zero owning
    rows. The retired enforcer never checked this direction: its schema had no notion
    of section completeness, only per-row validity."""
    owned = {_section_title(row["section"]) for row in map_data["rows"]}
    return sorted(law_titles - owned)


# --------------------------------------------------------------------------- #
# D14/A10.4 — hash-tuple staleness. Every message names what to re-read.
# --------------------------------------------------------------------------- #


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_text(path.read_text(encoding="utf-8"))


def _find_stale_hash_tuples(
    map_data: dict[str, Any],
    law_sections: dict[str, str],
    skills_dir: Path = _SKILLS_DIR,
    repo_root: Path = _REPO_ROOT,
) -> list[str]:
    violations: list[str] = []
    for row in map_data["rows"]:
        title = _section_title(row["section"])
        body = law_sections.get(title)
        if body is not None:
            real_section_hash = _sha256_text(body)
            if real_section_hash != row["hash_tuple"]["section"]:
                violations.append(
                    f"row(skill={row['skill']!r}): section hash stale for {row['section']!r} — "
                    f"re-read `dadaia_workspace/public/data/DADAIA.md` {row['section']} and "
                    "re-record hash_tuple.section"
                )
        if row["skill"] is not None:
            skill_path = skills_dir / row["skill"] / "SKILL.md"
            if skill_path.exists():
                real_skill_hash = _sha256_file(skill_path)
                if real_skill_hash != row["hash_tuple"]["skill"]:
                    rel = skill_path.relative_to(repo_root).as_posix()
                    violations.append(
                        f"row(skill={row['skill']!r}): skill hash stale — re-read `{rel}` "
                        "and re-record hash_tuple.skill"
                    )
        recorded_scoped = row["hash_tuple"]["scoped"]
        scoped_paths = row["scoped_agents_md"]
        if len(recorded_scoped) != len(scoped_paths):
            violations.append(
                f"row(skill={row['skill']!r}): hash_tuple.scoped has {len(recorded_scoped)} "
                f"entries but scoped_agents_md has {len(scoped_paths)} — re-read the row and "
                "re-record hash_tuple.scoped"
            )
            continue
        for rel, recorded_hash in zip(scoped_paths, recorded_scoped, strict=True):
            path = repo_root / rel
            if not path.exists():
                continue  # dangling reference — already flagged by the member check
            real_hash = _sha256_file(path)
            if real_hash != recorded_hash:
                violations.append(
                    f"row(skill={row['skill']!r}): scoped_agents_md hash stale for `{rel}` — "
                    f"re-read `{rel}` and re-record hash_tuple.scoped"
                )
    return violations


# --------------------------------------------------------------------------- #
# Ported mode 5 — SKILL.md line ceiling (G12). Unchanged: independent of row shape.
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
# Ported mode 6 — undeclared applyTo activation-glob overlap. Unchanged: independent
# of row shape (reads declared_overlaps + SKILL.md frontmatter).
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
# Ported checks — green at HEAD (A9.1's discipline, carried into A10.2).
# --------------------------------------------------------------------------- #


def test_every_mapped_section_exists_in_the_law() -> None:
    violations = _find_missing_sections(_real_map(), _law_section_titles())
    assert violations == [], f"row(s) point at a section absent from the law: {violations}"


def test_every_member_on_disk_is_mapped() -> None:
    """D14 — folds the retired `test_every_skill_on_disk_is_mapped` (skill arm) and
    extends it to the new scoped-AGENTS.md member type (see the name-diff)."""
    violations = _find_unmapped_members(_real_map(), _skills_on_disk(), _scoped_agents_md_sources())
    assert violations == [], f"member(s) on disk with no row: {violations}"


def test_every_mapped_member_exists_on_disk() -> None:
    """D14 — folds the retired `test_every_mapped_skill_exists_on_disk` (skill arm)
    and extends it to the new scoped-AGENTS.md member type (see the name-diff)."""
    violations = _find_dangling_member_references(
        _real_map(), _skills_on_disk(), _scoped_agents_md_sources()
    )
    assert violations == [], f"row(s) name a member absent from disk: {violations}"


def test_no_member_maps_to_two_sections() -> None:
    violations = _find_members_mapped_to_two_sections(_real_map())
    assert violations == [], f"member(s) claimed by more than one row: {violations}"


def test_every_law_section_has_an_owner() -> None:
    violations = _find_sections_without_an_owner(_real_map(), _law_section_titles())
    assert violations == [], f"DADAIA.md section(s) with zero owning rows: {violations}"


def test_every_hash_tuple_is_current() -> None:
    violations = _find_stale_hash_tuples(_real_map(), _law_section_bodies())
    assert violations == [], "stale hash_tuple(s) — re-record after review:\n" + "\n".join(
        violations
    )


def test_every_skill_md_is_within_the_declared_line_ceiling() -> None:
    violations = _find_ceiling_violations(_real_map(), _SKILLS_DIR)
    assert violations == [], f"SKILL.md(s) over the declared ceiling: {violations}"


def test_no_undeclared_activation_glob_overlap() -> None:
    violations = _find_undeclared_activation_overlaps(_real_map(), _SKILLS_DIR)
    assert violations == [], f"undeclared applyTo overlap(s): {violations}"


# --------------------------------------------------------------------------- #
# Ported mutation fixtures 1/5/6 — unchanged (see the name-diff for 2/3/4's fate).
# --------------------------------------------------------------------------- #


def test_mutation_fixture_1_missing_section_turns_red() -> None:
    mutated = copy.deepcopy(_real_map())
    mutated["rows"][0]["section"] = "§4 A Section Title That Does Not Exist"
    violations = _find_missing_sections(mutated, _law_section_titles())
    assert violations, "a row pointing at a nonexistent section title must be flagged"


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
# D14 — the five NEW mutation fixtures (A10.2). Bug citations
# (`citation-enforcer-resolves-projected-instance-paths-against-the-checkout`,
# `citation-mutation-fixtures-never-turn-red-on-windows`): module docstring. Every
# fixture builds its corrupted data purely in-memory (`copy.deepcopy` of the real
# map, or a fabricated string) — never touches a real repo file, and never depends
# on the host OS path separator, so the RED direction is provable identically on
# POSIX and Windows CI runners (the exact class the second cited bug fired on).
# --------------------------------------------------------------------------- #


def test_mutation_fixture_a_member_without_a_row_turns_red() -> None:
    """RED condition 1 — a skill AND a scoped AGENTS.md source, each added to the
    on-disk population without a corresponding row, must both be flagged. Extends the
    retired `test_mutation_fixture_2_unmapped_skill_turns_red`, which proved only the
    skill arm; the scoped-AGENTS.md arm is new territory this map adds."""
    mutated_skills = _skills_on_disk() | {"fixture-orphan-skill"}
    mutated_scoped = _scoped_agents_md_sources() | {
        "dadaia_workspace/public/data/fixture-orphan-AGENTS.md"
    }
    violations = _find_unmapped_members(_real_map(), mutated_skills, mutated_scoped)
    assert violations == [
        "skill:fixture-orphan-skill",
        "scoped_agents_md:dadaia_workspace/public/data/fixture-orphan-AGENTS.md",
    ]


def test_mutation_fixture_b_row_without_a_member_turns_red() -> None:
    """RED condition 2 — a row naming a skill path, and a row naming a scoped
    AGENTS.md path, that resolve to nothing on disk must both be flagged. Extends the
    retired `test_mutation_fixture_3_missing_skill_on_disk_turns_red`, which proved
    only the skill arm."""
    mutated = copy.deepcopy(_real_map())
    mutated["rows"][0]["skill"] = "fixture-nonexistent-skill"
    mutated["rows"][1]["scoped_agents_md"] = [
        "dadaia_workspace/public/data/fixture-nonexistent-AGENTS.md"
    ]
    violations = _find_dangling_member_references(
        mutated, _skills_on_disk(), _scoped_agents_md_sources()
    )
    assert violations == [
        "skill:fixture-nonexistent-skill",
        "scoped_agents_md:dadaia_workspace/public/data/fixture-nonexistent-AGENTS.md",
    ]


def test_mutation_fixture_c_member_maps_to_two_sections_turns_red() -> None:
    """RED condition 3 (A10.1) — a skill duplicated across two rows must be flagged
    even when it is the SAME real, correctly-mapped skill; the violation is the
    duplicate ownership itself, regardless of which section either row names. No
    counterpart in the retired enforcer — its schema made this structurally
    impossible to represent (a skill lived in at most one row's `skills` array by
    hand-curation), so it was never a checkable condition until rows became looser."""
    mutated = copy.deepcopy(_real_map())
    duplicate_row = copy.deepcopy(mutated["rows"][0])
    target_skill = mutated["rows"][1]["skill"]
    assert target_skill is not None, "fixture precondition: rows[1] must own a skill"
    duplicate_row["skill"] = target_skill
    mutated["rows"].append(duplicate_row)
    violations = _find_members_mapped_to_two_sections(mutated)
    assert violations == [f"skill:{target_skill}"]


def test_mutation_fixture_d_section_without_an_owner_turns_red() -> None:
    """RED condition 4 (A10.1, the inverse cardinality direction) — a `DADAIA.md`
    section with zero owning rows must be flagged. The retired enforcer never checked
    this direction: its schema had no notion of section completeness. A fabricated
    title is unioned into the law-titles set (never a real section demoted) — the
    fixture only needs a title no row owns, which this guarantees without touching
    any of the map's real, correctly-owned sections."""
    orphaned_title = "A Section Title That Definitely Does Not Own Anything Fixture"
    law_titles = _law_section_titles() | {orphaned_title}
    violations = _find_sections_without_an_owner(_real_map(), law_titles)
    assert violations == [orphaned_title]


def test_mutation_fixture_e_stale_hash_tuple_turns_red() -> None:
    """RED condition 5 (A10.4) — a member whose real content diverges from its row's
    recorded `hash_tuple` entry must be flagged: both the section-hash side and the
    skill-hash side, proven independently. Regression context (module docstring): an
    un-checked hash is exactly what lets a stale citation happen silently — a member
    moves, the map does not notice."""
    mutated = copy.deepcopy(_real_map())
    fabricated_hash = "sha256:" + "0" * 64
    mutated["rows"][0]["hash_tuple"]["skill"] = fabricated_hash
    mutated["rows"][1]["hash_tuple"]["section"] = fabricated_hash
    law_sections = _law_section_bodies()

    violations = _find_stale_hash_tuples(mutated, law_sections)

    assert any("skill hash stale" in v for v in violations), violations
    assert any("section hash stale" in v for v in violations), violations


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
# FR28 (T-044-56, A28.1) — ported verbatim. The invocation model, checked in BOTH
# directions, no hand-kept list. The grant set is DERIVED: the union of every persona
# frontmatter's `skills:` allowlist, plus the same universal-grant mechanism
# failure mode 6 already special-cases.
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


# --------------------------------------------------------------------------- #
# FR27/A27.20 (T-044-58) — ported verbatim. Citable-pattern definition and
# exclusion rules: module docstring. Command-tree derivation choice (import, never
# subprocess) and its justification: module docstring.
# --------------------------------------------------------------------------- #


@functools.lru_cache(maxsize=1)
def _derive_command_tree() -> frozenset[tuple[str, ...]]:
    """Walk the REAL Typer app (never a subprocess ``--help`` parse — see module
    docstring for the hermetic/fast/always-in-sync justification), once per run.

    Walked by duck-typing (``hasattr(cmd, "commands")``), never
    ``isinstance(cmd, click.Group)``: the installed ``typer`` (``>=0.27.1``) vendors its
    own click-compatible core (``typer._click.core``), so ``typer.core.TyperGroup`` does
    NOT subclass the external ``click.Group`` — an ``isinstance`` check silently walks
    zero children. Duck-typing is the version-robust choice across typer/click pairings.
    """
    from dadaia_workspace.cli.main import app as _app

    root = get_command(_app)
    paths: set[tuple[str, ...]] = {()}

    def _walk(cmd: object, prefix: tuple[str, ...]) -> None:
        commands = getattr(cmd, "commands", None)
        if not isinstance(commands, dict):
            return
        for name, sub in commands.items():
            child = prefix + (name,)
            paths.add(child)
            _walk(sub, child)

    _walk(root, ())
    return frozenset(paths)


# Pinned, derived-with-a-pin (module docstring's fix note): the ONE specs_dir-relative
# path this corpus cites that is a projected INSTANCE reality, never a checkout reality
# (bug citation-enforcer-resolves-projected-instance-paths-against-the-checkout). The
# name is pinned here; the companion assertion inside _projected_specs_agents_relpath —
# executing the REAL installer mapping and diffing byte-for-byte against its generating
# public asset — is what keeps this constant honest, never a second hand-kept allowlist.
_PROJECTED_SPECS_TARGET_RELPATH = "AGENTS.md"
_SPECS_AGENTS_SOURCE_TEMPLATE = "specs-AGENTS.md"


@functools.cache
def _projected_specs_agents_relpath(repo_root: Path) -> str | None:
    """Prove — by actually EXECUTING the real installer mapping, never a second
    hand-kept allowlist (D4/D10) — that ``specs/AGENTS.md`` is a projected INSTANCE
    path: ``dadaia_workspace.features.specs.scaffolder.scaffold`` writes it from
    ``dadaia_workspace/public/templates/specs-AGENTS.md`` (the generating public asset)
    into any ``<specs_dir>/AGENTS.md`` — at the workspace root and inside every
    ``repos/<slug>/`` alike. It is deliberately never tracked in ANY checkout of this
    library repo, so a bare clone never has it on disk even though a
    locally-instantiated workspace carries it as an untracked lib-projection leftover.

    Runs ``scaffold()`` against a throwaway scratch directory and confirms the produced
    ``AGENTS.md`` is byte-identical to the real source template — proof by generating
    asset, never by checkout presence. Returns ``None`` (never special-cased) when the
    source template itself is absent under *repo_root*."""
    templates_dir = repo_root / "dadaia_workspace" / "public" / "templates"
    source = templates_dir / _SPECS_AGENTS_SOURCE_TEMPLATE
    if not source.exists():
        return None

    from dadaia_workspace.features.specs.scaffolder import scaffold

    with tempfile.TemporaryDirectory() as scratch:
        scratch_specs_dir = Path(scratch) / "specs"
        result = scaffold(
            specs_dir=scratch_specs_dir,
            project_name="citation-enforcer-projection-probe",
            force=True,
            templates_dir=templates_dir,
        )
        target = scratch_specs_dir / _PROJECTED_SPECS_TARGET_RELPATH
        if result.errors or target not in result.created:
            return None
        if target.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
            return None
    return _PROJECTED_SPECS_TARGET_RELPATH


def _is_placeholder_or_ellipsis(token: str) -> bool:
    if any(ch in _PLACEHOLDER_CHARS for ch in token):
        return True
    return any(marker in token for marker in _ELLIPSIS_MARKERS)


def _sibling_marked(same_line_remainder: str, next_line: str) -> bool:
    """True if the ``(sibling)``/``sibling`` annotation follows the citation, either on
    the same line or on the very next line — a blockquote continuation, whose leading
    ``>`` marker is stripped first."""
    if _SIBLING_MARKER_RE.match(same_line_remainder.lstrip()):
        return True
    stripped_next = _BLOCKQUOTE_PREFIX_RE.sub("", next_line).lstrip()
    return bool(_SIBLING_MARKER_RE.match(stripped_next))


def _posix_relpath(path: PurePath, root: PurePath) -> str:
    """Render ``path`` relative to ``root`` in POSIX form — separator-agnostic, so a
    violation's ``file:line`` citation is byte-identical whether the check runs on
    Windows or POSIX (bug ``citation-mutation-fixtures-never-turn-red-on-windows``).
    ``relative_to``/``as_posix`` are pure path arithmetic (no I/O), so this seam takes
    any ``PurePath`` — including a ``PureWindowsPath`` on a non-Windows host, which is
    exactly how the regression test below drives it without needing Windows CI."""
    return path.relative_to(root).as_posix()


def _find_dead_path_citations(public_dir: Path, repo_root: Path) -> list[str]:
    """Failure mode (a) — every ``specs/``/``dadaia_workspace/``/``.github/``-prefixed
    or ``(sibling)``-annotated bare-filename citation in every ``*.md`` under
    ``public_dir`` must resolve on disk. Returns ``file:line: dead ... `token` `` strings
    (A27.20 — fails naming the file:line and the dead path)."""
    violations: list[str] = []
    for md_path in sorted(public_dir.glob("**/*.md")):
        lines = md_path.read_text(encoding="utf-8").splitlines()
        rel = _posix_relpath(md_path, repo_root)
        for idx, line in enumerate(lines):
            for m in _CITATION_BACKTICK_RE.finditer(line):
                token = m.group(1).strip()
                if not token or _is_placeholder_or_ellipsis(token):
                    continue
                if token.startswith(_WORKSPACE_RUNTIME_PREFIX):
                    continue
                if token.startswith(_CITABLE_PATH_PREFIXES):
                    projected_relpath = _projected_specs_agents_relpath(repo_root)
                    if projected_relpath is not None and token == f"specs/{projected_relpath}":
                        continue
                    if not (repo_root / token).exists():
                        violations.append(f"{rel}:{idx + 1}: dead path `{token}`")
                    continue
                if "/" in token or not _SIBLING_FILENAME_RE.match(token):
                    continue
                next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
                if not _sibling_marked(line[m.end() :], next_line):
                    continue
                if (md_path.parent / token).exists():
                    continue
                if any(public_dir.glob(f"**/{token}")):
                    continue
                violations.append(f"{rel}:{idx + 1}: dead sibling citation `{token}`")
    return violations


def _find_dead_verb_citations(
    public_dir: Path, repo_root: Path, tree: frozenset[tuple[str, ...]]
) -> list[str]:
    """Failure mode (b) — every ``dadaia <verb> [<sub>]`` citation in every ``*.md``
    under ``public_dir`` must resolve in the live command tree. Returns
    ``file:line: dead verb ... `` strings (A27.20 — fails naming the file:line and the
    dead verb)."""
    violations: list[str] = []
    for md_path in sorted(public_dir.glob("**/*.md")):
        lines = md_path.read_text(encoding="utf-8").splitlines()
        rel = _posix_relpath(md_path, repo_root)
        for idx, line in enumerate(lines):
            for m in _CITATION_BACKTICK_RE.finditer(line):
                token = m.group(1)
                for cm in _DADAIA_VERB_RE.finditer(token):
                    v1, v2 = cm.group(1), cm.group(2)
                    if v1 is None:
                        verb_path: tuple[str, ...] = ()
                    elif v2 is None:
                        verb_path = (v1,)
                    else:
                        verb_path = (v1, v2)
                    if not verb_path or verb_path in tree:
                        continue
                    violations.append(
                        f"{rel}:{idx + 1}: dead verb `dadaia {' '.join(verb_path)}` "
                        f"(cited as `{token.strip()}`)"
                    )
    return violations


def test_every_cited_path_exists() -> None:
    violations = _find_dead_path_citations(_PUBLIC, _REPO_ROOT)
    assert violations == [], "dead path citation(s):\n" + "\n".join(violations)


def test_projected_specs_agents_md_citation_survives_bare_checkout() -> None:
    """Regression — bug ``citation-enforcer-resolves-projected-instance-paths-
    against-the-checkout`` (HIGH). ``specs/AGENTS.md`` is cited by public docs; it is
    an INSTANCE reality that
    ``dadaia_workspace.features.specs.scaffolder.scaffold`` projects from
    ``dadaia_workspace/public/templates/specs-AGENTS.md``, which this repo's own
    ``.gitignore``/repo-hygiene job both forbid ever tracking — so a bare CI clone
    never has it on disk even though a locally-instantiated workspace does. This test
    proves the check no longer depends on that presence difference: it hides the real
    local leftover (if any) — never deletes it — before scanning, and restores it
    unconditionally, so the exact bare-checkout condition CI hits is exercised locally
    too."""
    real_path = _REPO_ROOT / "specs" / "AGENTS.md"
    hidden_path = real_path.with_name("AGENTS.md.hidden-for-bare-checkout-test")
    moved = False
    if real_path.exists():
        real_path.rename(hidden_path)
        moved = True
    try:
        assert not (_REPO_ROOT / "specs" / "AGENTS.md").exists(), (
            "fixture precondition: specs/AGENTS.md must be absent to simulate a bare checkout"
        )
        violations = _find_dead_path_citations(_PUBLIC, _REPO_ROOT)
    finally:
        if moved:
            hidden_path.rename(real_path)
    dead_specs_agents = [v for v in violations if "specs/AGENTS.md" in v]
    assert dead_specs_agents == [], (
        "citation(s) of the projected instance path `specs/AGENTS.md` resolved against "
        "checkout presence instead of its generating public asset:\n" + "\n".join(dead_specs_agents)
    )


def test_every_cited_dadaia_verb_exists() -> None:
    tree = _derive_command_tree()
    violations = _find_dead_verb_citations(_PUBLIC, _REPO_ROOT, tree)
    assert violations == [], "dead dadaia verb citation(s):\n" + "\n".join(violations)


def test_mutation_fixture_9_dead_path_citation_turns_red(tmp_path: Path) -> None:
    """A27.20 mutation fixture — dead path. A fixture asset citing a `specs/`-prefixed
    path that does not exist under a fixture repo root must be flagged. Never touches a
    real repo file: `repo_root` and `public_dir` are both under `tmp_path`."""
    fixture_repo_root = tmp_path / "fixture-repo"
    fixture_public = fixture_repo_root / "dadaia_workspace" / "public" / "skills" / "fixture-skill"
    fixture_public.mkdir(parents=True)
    (fixture_public / "SKILL.md").write_text(
        "See `specs/this-path-does-not-exist-fixture.md` for detail.\n", encoding="utf-8"
    )

    violations = _find_dead_path_citations(
        fixture_repo_root / "dadaia_workspace" / "public", fixture_repo_root
    )
    assert len(violations) == 1
    assert "specs/this-path-does-not-exist-fixture.md" in violations[0]
    assert violations[0].startswith("dadaia_workspace/public/skills/fixture-skill/SKILL.md:1:")


def test_mutation_fixture_11_lookalike_projected_path_still_turns_red(tmp_path: Path) -> None:
    """Bug ``citation-enforcer-resolves-projected-instance-paths-against-the-checkout``
    follow-up mutation fixture — both directions (a cited path absent from the checkout
    AND absent from the known projection target still fails). A `specs/`-prefixed
    citation that merely resembles the ONE projected target this fix special-cases
    (``specs/AGENTS.md`` — wrong nesting here) must still be flagged. Never touches a
    real repo file: `repo_root` and `public_dir` are both under `tmp_path`."""
    fixture_repo_root = tmp_path / "fixture-repo"
    fixture_public = fixture_repo_root / "dadaia_workspace" / "public" / "skills" / "fixture-skill"
    fixture_public.mkdir(parents=True)
    (fixture_public / "SKILL.md").write_text(
        "See `specs/nested/AGENTS.md` for detail.\n", encoding="utf-8"
    )

    violations = _find_dead_path_citations(
        fixture_repo_root / "dadaia_workspace" / "public", fixture_repo_root
    )
    assert len(violations) == 1
    assert "specs/nested/AGENTS.md" in violations[0]
    assert violations[0].startswith("dadaia_workspace/public/skills/fixture-skill/SKILL.md:1:")


def test_mutation_fixture_10_dead_verb_citation_turns_red(tmp_path: Path) -> None:
    """A27.20 mutation fixture — dead verb. A fixture asset citing a `dadaia` verb pair
    absent from the real command tree must be flagged. Never touches a real repo file."""
    fixture_repo_root = tmp_path / "fixture-repo"
    fixture_public = fixture_repo_root / "dadaia_workspace" / "public" / "skills" / "fixture-skill"
    fixture_public.mkdir(parents=True)
    (fixture_public / "SKILL.md").write_text(
        "Run `dadaia fixture-nonexistent-verb now`.\n", encoding="utf-8"
    )

    tree = _derive_command_tree()
    violations = _find_dead_verb_citations(
        fixture_repo_root / "dadaia_workspace" / "public", fixture_repo_root, tree
    )
    assert len(violations) == 1
    assert "dadaia fixture-nonexistent-verb now" in violations[0]
    assert violations[0].startswith("dadaia_workspace/public/skills/fixture-skill/SKILL.md:1:")


def test_posix_relpath_is_separator_agnostic_under_windows_path_semantics() -> None:
    """Regression — bug `citation-mutation-fixtures-never-turn-red-on-windows` (HIGH).
    On windows-latest CI, `_find_dead_path_citations`/`_find_dead_verb_citations`
    correctly DETECTED the planted violation (`len(violations) == 1`, correct token) —
    the bug was never a vacuous no-op. It was the violation's `file:line` prefix
    rendering with the OS-native separator (backslash on Windows) instead of the
    POSIX form every consumer of a `file:line` citation expects. `PureWindowsPath`
    proves the fixed seam produces POSIX output even when built from genuine Windows
    path semantics, on any host OS."""
    windows_root = PureWindowsPath(r"D:\pytest-fixture-repo")
    windows_md_path = (
        windows_root / "dadaia_workspace" / "public" / "skills" / "fixture-skill" / "SKILL.md"
    )

    rel = _posix_relpath(windows_md_path, windows_root)

    assert rel == "dadaia_workspace/public/skills/fixture-skill/SKILL.md"
    assert "\\" not in rel
