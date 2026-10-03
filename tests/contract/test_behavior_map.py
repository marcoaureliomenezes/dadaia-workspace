"""One enforcer for the behavior map (T-050-19).

Intent: CONTRACT — A10.1-A10.6 (SPEC v0.5.0); FR27 citations, FR28 grants. Size: SMALL.

- One map (`public/entities/behavior-map.json`), one schema, this one enforcer; every member (a
  skill, or a scoped `AGENTS.md` SOURCE under `public/{data,scaffold,templates}/`) maps to exactly
  one row, every root-map section has an owner, every `hash_tuple` is current (A10.1, A10.4).
- `scoped_agents_md` names SOURCE paths, never the projected instance path — bug
  `citation-enforcer-resolves-projected-instance-paths-against-the-checkout`.
- Every violation is built from POSIX-relative paths and every planted fixture is in-memory or
  under `tmp_path` — bug `citation-mutation-fixtures-never-turn-red-on-windows`.
- Each check has a planted violation that turns it red (A10.2).
"""

from __future__ import annotations

import ast
import copy
import functools
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter
from collections.abc import Callable
from itertools import combinations
from pathlib import Path, PureWindowsPath
from typing import Any

import jsonschema
import pytest

from dadaia_workspace.cli.help_digest import command_paths
from dadaia_workspace.features.specs.citations import (
    dead_body_pointers_in_tree,
    dead_path_citations_in_tree,
    dead_verb_citations_in_tree,
    posix_relpath,
)
from dadaia_workspace.infrastructure.public_assets import (
    _SKILL_SCRIPT_SCHEMAS,  # allow-private-import: the one staging table naming which shipped schema each skill script carries a copy of; a second table here is the fork this hash guards against
)
from dadaia_workspace.infrastructure.public_assets_common import iter_public_files
from tests.helpers.scan_population import assert_populated

pytestmark = pytest.mark.contract

_PKG_ROOT = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_PUBLIC = _PKG_ROOT / "public"
_MAP_PATH = _PUBLIC / "entities" / "behavior-map.json"
_SCHEMA_PATH = _PUBLIC / "schemas" / "behavior-map-v1.schema.json"
_LAW_PATH = _PUBLIC / "data" / "AGENTS.md"
_SKILLS_DIR = _PUBLIC / "skills"
_AGENTS_DIR = _PUBLIC / "agents"
_REPO_ROOT = _PKG_ROOT.parent

_HEADING_RE = re.compile(r"^##\s+\d+\.\s+(.+?)\s*$", re.MULTILINE)
_SECTION_FIELD_RE = re.compile(r"^§\d+\s+(.+)$")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_APPLYTO_RE = re.compile(r'^applyTo:\s*"?([^"\n]*)"?\s*$', re.MULTILINE)
_SKILLS_LIST_RE = re.compile(r"^skills:\s*\n((?:  - .+\n)+)", re.MULTILINE)
_DISABLE_MODEL_INVOCATION_RE = re.compile(
    r"^disable-model-invocation:\s*true\s*$", re.MULTILINE | re.IGNORECASE
)

#: Skills whose activation surface is intentionally universal (from the retired collision lint).
_UNIVERSAL_GLOBS: frozenset[str] = frozenset({"**"})
_UNIVERSAL_NAMES: frozenset[str] = frozenset({"dd-grill-me"})

_SCOPED_SUBDIRS = ("data", "scaffold", "templates")
#: The root map is the law source itself, never a scoped rule.
_LAW_SOURCE_RELPATH = "dadaia_workspace/public/data/AGENTS.md"


def _load_json(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _real_map() -> dict[str, Any]:
    return _load_json(_MAP_PATH)


def _law_section_titles(law_path: Path = _LAW_PATH) -> set[str]:
    return {m.group(1).strip() for m in _HEADING_RE.finditer(law_path.read_text(encoding="utf-8"))}


def _law_section_bodies(law_path: Path = _LAW_PATH) -> dict[str, str]:
    """Title -> the span `hash_tuple.section` hashes: its heading up to the next one (A10.4)."""
    text = law_path.read_text(encoding="utf-8")
    heads = list(_HEADING_RE.finditer(text))
    return {
        m.group(1).strip(): text[m.start() : heads[i + 1].start() if i + 1 < len(heads) else None]
        for i, m in enumerate(heads)
    }


def _section_title(section_field: str) -> str:
    m = _SECTION_FIELD_RE.match(section_field)
    if m is None:
        raise ValueError(f"section field is not title-anchored ('§N <Title>'): {section_field!r}")
    return m.group(1).strip()


def _skills_on_disk(skills_dir: Path = _SKILLS_DIR) -> set[str]:
    skills = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    assert_populated(skills, sentinel="dd-cli-library")
    return skills


def _scoped_agents_md_sources(public_dir: Path = _PUBLIC) -> set[str]:
    """Globbed from the generators, never a hand-written roster."""
    found = {
        "dadaia_workspace/public/" + p.relative_to(public_dir).as_posix()
        for sub in _SCOPED_SUBDIRS
        for pattern in ("**/AGENTS.md", "**/*-AGENTS.md")
        for p in (public_dir / sub).glob(pattern)
    } - {_LAW_SOURCE_RELPATH}
    assert_populated(found, sentinel="dadaia_workspace/public/scaffold/bugs/AGENTS.md")
    return found


def _members(map_data: dict[str, Any]) -> tuple[list[str], list[str]]:
    rows = map_data["rows"]
    return (
        [row["skill"] for row in rows if row["skill"] is not None],
        [p for row in rows for p in row["scoped_agents_md"]],
    )


def _find_missing_sections(map_data: dict[str, Any], law_titles: set[str]) -> list[str]:
    return [
        f"skill={row['skill']!r}: section {row['section']!r} is no '## N. <Title>' heading of the law"
        for row in map_data["rows"]
        if _section_title(row["section"]) not in law_titles
    ]


def _member_diff(left: tuple[set[str], set[str]], right: tuple[set[str], set[str]]) -> list[str]:
    return [f"skill:{s}" for s in sorted(left[0] - right[0])] + [
        f"scoped_agents_md:{s}" for s in sorted(left[1] - right[1])
    ]


def _find_unmapped_members(
    map_data: dict[str, Any], skills: set[str], scoped_sources: set[str]
) -> list[str]:
    skills_mapped, scoped_mapped = _members(map_data)
    return _member_diff((skills, scoped_sources), (set(skills_mapped), set(scoped_mapped)))


def _find_dangling_member_references(
    map_data: dict[str, Any], skills: set[str], scoped_sources: set[str]
) -> list[str]:
    skills_mapped, scoped_mapped = _members(map_data)
    return _member_diff((set(skills_mapped), set(scoped_mapped)), (skills, scoped_sources))


def _find_members_mapped_to_two_sections(map_data: dict[str, Any]) -> list[str]:
    """A10.1: the row is the ownership unit — a member in two rows is ambiguous, same section or not."""
    skills, scoped = _members(map_data)
    return [f"skill:{k}" for k, v in sorted(Counter(skills).items()) if v > 1] + [
        f"scoped_agents_md:{k}" for k, v in sorted(Counter(scoped).items()) if v > 1
    ]


def _find_sections_without_an_owner(map_data: dict[str, Any], law_titles: set[str]) -> list[str]:
    return sorted(law_titles - {_section_title(row["section"]) for row in map_data["rows"]})


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_text(path.read_text(encoding="utf-8"))


def _script_members(skill: str, skills_dir: Path, public_dir: Path) -> list[tuple[str, Path]]:
    """Every file `stage` copies from the skill's `scripts/` (its one walk) plus, as `schemas/<name>`, the shipped
    original of each schema `stage` copies beside them — so a schema fork is red on both sides."""
    scripts_dir = skills_dir / skill / "scripts"
    members = [
        (path.relative_to(scripts_dir).as_posix(), path)
        for path in iter_public_files(scripts_dir)
        if "schemas" not in path.relative_to(scripts_dir).parts
    ]
    return members + sorted(
        {
            (f"schemas/{Path(schema_rel).name}", public_dir / schema_rel)
            for schema_rel, scripts_rel in _SKILL_SCRIPT_SCHEMAS
            if scripts_rel.split("/")[1] == skill
        }
    )


def _scripts_hash(skill: str, skills_dir: Path, public_dir: Path) -> str | None:
    members = _script_members(skill, skills_dir, public_dir)
    if not members:
        return None
    return _sha256_text("".join(f"{name}:{_sha256_file(path)}\n" for name, path in members))


def _find_stale_hash_tuples(
    map_data: dict[str, Any],
    law_sections: dict[str, str],
    skills_dir: Path = _SKILLS_DIR,
    repo_root: Path = _REPO_ROOT,
    public_dir: Path = _PUBLIC,
) -> list[str]:
    """Every message names what to re-read (A10.4)."""
    violations: list[str] = []
    for row in map_data["rows"]:
        who, recorded = f"row(skill={row['skill']!r})", row["hash_tuple"]
        body = law_sections.get(_section_title(row["section"]))
        if body is not None and _sha256_text(body) != recorded["section"]:
            violations.append(
                f"{who}: section hash stale for {row['section']!r} — re-read "
                f"`dadaia_workspace/public/data/AGENTS.md` {row['section']} and re-record hash_tuple.section"
            )
        if row["skill"] is not None:
            skill_path = skills_dir / row["skill"] / "SKILL.md"
            if skill_path.exists() and _sha256_file(skill_path) != recorded["skill"]:
                rel = skill_path.relative_to(repo_root).as_posix()
                violations.append(
                    f"{who}: skill hash stale — re-read `{rel}` and re-record hash_tuple.skill"
                )
            if (skills_dir / row["skill"] / "scripts").is_dir() and _scripts_hash(
                row["skill"], skills_dir, public_dir
            ) != recorded["scripts"]:
                violations.append(
                    f"{who}: scripts hash stale — re-read every file under `{row['skill']}/scripts/` "
                    "and the shipped schemas it carries, and re-record hash_tuple.scripts"
                )
        scoped_paths = row["scoped_agents_md"]
        if len(recorded["scoped"]) != len(scoped_paths):
            violations.append(
                f"{who}: hash_tuple.scoped has {len(recorded['scoped'])} entries but "
                f"scoped_agents_md has {len(scoped_paths)} — re-read the row and re-record hash_tuple.scoped"
            )
            continue
        violations += [
            f"{who}: scoped_agents_md hash stale for `{rel}` — re-read `{rel}` and re-record hash_tuple.scoped"
            for rel, recorded_hash in zip(scoped_paths, recorded["scoped"], strict=True)
            if (repo_root / rel).exists() and _sha256_file(repo_root / rel) != recorded_hash
        ]
    return violations


def _find_ceiling_violations(map_data: dict[str, Any], skills_dir: Path) -> list[str]:
    ceiling = map_data["skill_md_line_ceiling"]
    return [
        f"{md.parent.name}: {n} lines > ceiling {ceiling}"
        for md in sorted(skills_dir.glob("*/SKILL.md"))
        if (n := len(md.read_text(encoding="utf-8").splitlines())) > ceiling
    ]


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    parts = re.split(r"(\*\*|\*)", glob)
    body = "".join({"**": ".*", "*": "[^/]*"}.get(p, re.escape(p)) for p in parts)
    return re.compile("^" + body + "$")


def _globs_overlap(glob_a: str, glob_b: str) -> bool:
    """True if one glob matches a concrete path instantiated from the other."""

    def probe(glob: str) -> str:
        return glob.replace("**", "x/y/z").replace("*", "x")

    return (
        glob_a == glob_b
        or bool(_glob_to_regex(glob_b).match(probe(glob_a)))
        or bool(_glob_to_regex(glob_a).match(probe(glob_b)))
    )


def _frontmatter(md_path: Path) -> str:
    fm = _FRONTMATTER_RE.match(md_path.read_text(encoding="utf-8"))
    return fm.group(1) if fm else ""


def _skill_name_and_apply_to(skills_dir: Path) -> list[tuple[str, str]]:
    found = []
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        raw = _frontmatter(md)
        if name := _NAME_RE.search(raw):
            apply_to = _APPLYTO_RE.search(raw)
            found.append((name.group(1), apply_to.group(1).strip() if apply_to else ""))
    return found


def _find_overlap_pairs(
    stage_skills: list[tuple[str, str]], declared_groups: list[frozenset[str]]
) -> list[tuple[str, str]]:
    return [
        (name_a, name_b)
        for (name_a, glob_a), (name_b, glob_b) in combinations(stage_skills, 2)
        if _globs_overlap(glob_a, glob_b)
        and not any({name_a, name_b} <= group for group in declared_groups)
    ]


def _find_undeclared_activation_overlaps(
    map_data: dict[str, Any], skills_dir: Path
) -> list[tuple[str, str]]:
    stage = [
        (name, apply_to)
        for name, apply_to in _skill_name_and_apply_to(skills_dir)
        if apply_to and apply_to not in _UNIVERSAL_GLOBS and name not in _UNIVERSAL_NAMES
    ]
    return _find_overlap_pairs(stage, [frozenset(g) for g in map_data.get("declared_overlaps", [])])


def _granted_to_any_model(agents_dir: Path, skills_dir: Path) -> set[str]:
    """A28.1: every persona's `skills:` allowlist plus the universal-grant skills — derived."""
    granted = {
        line.strip()[2:].strip()
        for agent_md in sorted(agents_dir.glob("*.md"))
        if (m := _SKILLS_LIST_RE.search(_frontmatter(agent_md)))
        for line in m.group(1).splitlines()
        if line.strip()
    }
    return granted | {
        name
        for name, apply_to in _skill_name_and_apply_to(skills_dir)
        if name in _UNIVERSAL_NAMES or apply_to in _UNIVERSAL_GLOBS
    }


def _disable_model_invocation_flagged(skills_dir: Path) -> set[str]:
    return {
        md.parent.name
        for md in sorted(skills_dir.glob("*/SKILL.md"))
        if _DISABLE_MODEL_INVOCATION_RE.search(_frontmatter(md))
    }


def _find_flagged_but_granted(granted: set[str], flagged: set[str]) -> list[str]:
    return sorted(flagged & granted)


def test_map_validates_against_its_own_schema() -> None:
    jsonschema.validate(instance=_real_map(), schema=_load_json(_SCHEMA_PATH))


_REAL_CHECKS: dict[str, Callable[[], list[Any]]] = {
    "every-mapped-section-exists-in-the-law": lambda: _find_missing_sections(
        _real_map(), _law_section_titles()
    ),
    "every-member-on-disk-is-mapped": lambda: _find_unmapped_members(
        _real_map(), _skills_on_disk(), _scoped_agents_md_sources()
    ),
    "every-mapped-member-exists-on-disk": lambda: _find_dangling_member_references(
        _real_map(), _skills_on_disk(), _scoped_agents_md_sources()
    ),
    "no-member-maps-to-two-sections": lambda: _find_members_mapped_to_two_sections(_real_map()),
    "every-law-section-has-an-owner": lambda: _find_sections_without_an_owner(
        _real_map(), _law_section_titles()
    ),
    "every-hash-tuple-is-current": lambda: _find_stale_hash_tuples(
        _real_map(), _law_section_bodies()
    ),
    "every-skill-md-is-within-the-declared-line-ceiling": lambda: _find_ceiling_violations(
        _real_map(), _SKILLS_DIR
    ),
    "no-undeclared-activation-glob-overlap": lambda: _find_undeclared_activation_overlaps(
        _real_map(), _SKILLS_DIR
    ),
    "disable-model-invocation-skills-are-in-no-allowlist": lambda: _find_flagged_but_granted(
        _granted_to_any_model(_AGENTS_DIR, _SKILLS_DIR),
        _disable_model_invocation_flagged(_SKILLS_DIR),
    ),
    "every-cited-path-exists": lambda: _real_dead_path_citations(),
    "every-cited-dadaia-verb-exists": lambda: dead_verb_citations_in_tree(
        _PUBLIC, _REPO_ROOT, command_paths()
    ),
    "every-skill-body-pointer-resolves": lambda: dead_body_pointers_in_tree(
        (_SKILLS_DIR, _AGENTS_DIR), _PUBLIC, _REPO_ROOT
    ),
}


@pytest.mark.parametrize("check", list(_REAL_CHECKS))
def test_the_real_tree_passes_every_check(check: str) -> None:
    """A10.1-A10.4, FR27/FR28 over the shipped tree; `every-cited-path-exists` is
    sa-text-restates-rules-the-code-contradicts#49.6. Each check's planted red is below."""
    violations = _REAL_CHECKS[check]()
    assert violations == [], f"{check}:\n" + "\n".join(map(str, violations))


def _with(mutate: Callable[[dict[str, Any]], object]) -> dict[str, Any]:
    mutated = copy.deepcopy(_real_map())
    mutate(mutated)
    return mutated


def _set(row: int, key: str, value: object) -> Callable[[dict[str, Any]], object]:
    return lambda m: m["rows"][row].__setitem__(key, value)


def _duplicate_row1_skill(m: dict[str, Any]) -> None:
    m["rows"].append({**copy.deepcopy(m["rows"][0]), "skill": m["rows"][1]["skill"]})


_ZERO = "sha256:" + "0" * 64
_ORPHAN_TITLE = "A Section Title That Definitely Does Not Own Anything Fixture"


def _stale_skill_and_section(m: dict[str, Any]) -> None:
    m["rows"][0]["hash_tuple"]["skill"] = _ZERO
    m["rows"][1]["hash_tuple"]["section"] = _ZERO


_PLANTED: dict[str, tuple[Callable[[], list[Any]], Callable[[list[Any]], bool]]] = {
    "1-missing-section": (
        lambda: _find_missing_sections(
            _with(_set(0, "section", "§4 A Section Title That Does Not Exist")),
            _law_section_titles(),
        ),
        bool,
    ),
    "a-member-without-a-row": (
        lambda: _find_unmapped_members(
            _real_map(),
            _skills_on_disk() | {"fixture-orphan-skill"},
            _scoped_agents_md_sources() | {"dadaia_workspace/public/data/fixture-orphan-AGENTS.md"},
        ),
        lambda v: (
            v
            == [
                "skill:fixture-orphan-skill",
                "scoped_agents_md:dadaia_workspace/public/data/fixture-orphan-AGENTS.md",
            ]
        ),
    ),
    "b-row-without-a-member": (
        lambda: _find_dangling_member_references(
            _with(
                lambda m: (
                    _set(0, "skill", "fixture-nonexistent-skill")(m),
                    _set(
                        1,
                        "scoped_agents_md",
                        ["dadaia_workspace/public/data/fixture-nonexistent-AGENTS.md"],
                    )(m),
                )
            ),
            _skills_on_disk(),
            _scoped_agents_md_sources(),
        ),
        lambda v: (
            v
            == [
                "skill:fixture-nonexistent-skill",
                "scoped_agents_md:dadaia_workspace/public/data/fixture-nonexistent-AGENTS.md",
            ]
        ),
    ),
    "c-member-maps-to-two-sections": (
        lambda: _find_members_mapped_to_two_sections(_with(_duplicate_row1_skill)),
        lambda v: v == [f"skill:{_real_map()['rows'][1]['skill']}"],
    ),
    "d-section-without-an-owner": (
        lambda: _find_sections_without_an_owner(
            _real_map(), _law_section_titles() | {_ORPHAN_TITLE}
        ),
        lambda v: v == [_ORPHAN_TITLE],
    ),
    "e-stale-skill-and-section-hash": (
        lambda: _find_stale_hash_tuples(_with(_stale_skill_and_section), _law_section_bodies()),
        lambda v: (
            any("skill hash stale" in x for x in v) and any("section hash stale" in x for x in v)
        ),
    ),
    "self-test-a-universal-glob-never-fires": (
        lambda: _find_overlap_pairs([("some-stage", "specs/foo/**")], []),
        lambda v: v == [],
    ),
    "self-test-b-undeclared-duplicate-glob-fires": (
        lambda: _find_overlap_pairs(
            [
                ("fixture-skill-one", "specs/newthing/**"),
                ("fixture-skill-two", "specs/newthing/**"),
            ],
            [],
        ),
        lambda v: v == [("fixture-skill-one", "fixture-skill-two")],
    ),
    "8-flagged-skill-still-granted": (
        lambda: _find_flagged_but_granted(
            _granted_to_any_model(_AGENTS_DIR, _SKILLS_DIR), {"dd-code-review"}
        ),
        lambda v: v == ["dd-code-review"],
    ),
}


@pytest.mark.parametrize("case", list(_PLANTED))
def test_a_planted_map_violation_turns_red(case: str) -> None:
    """A10.2: each in-memory planted violation is flagged with its exact message."""
    run, expected = _PLANTED[case]
    violations = run()
    assert expected(violations), violations


def _write_skill(skills_dir: Path, name: str, text: str) -> None:
    (skills_dir / name).mkdir(parents=True)
    (skills_dir / name / "SKILL.md").write_text(text, encoding="utf-8")


def test_an_oversized_skill_md_and_an_undeclared_overlap_turn_red(tmp_path: Path) -> None:
    """A10.2 mutation fixtures 5 and 6, planted under tmp_path."""
    ceiling = _real_map()["skill_md_line_ceiling"]
    _write_skill(tmp_path / "big", "fixture-oversized-skill", "\n".join(["l"] * (ceiling + 20)))
    for name in ("fixture-skill-one", "fixture-skill-two"):
        _write_skill(
            tmp_path / "glob", name, f'---\nname: {name}\napplyTo: "specs/newthing/**"\n---\n'
        )

    assert [v.split(":")[0] for v in _find_ceiling_violations(_real_map(), tmp_path / "big")] == [
        "fixture-oversized-skill"
    ]
    assert _find_undeclared_activation_overlaps(_real_map(), tmp_path / "glob") == [
        ("fixture-skill-one", "fixture-skill-two")
    ]


def test_mutation_fixture_f_edited_skill_script_turns_red(tmp_path: Path) -> None:
    """A10.4 scripts side: one byte appended to a copied skill script is a stale scripts hash;
    planted bytecode is not (bug behavior-map-hash-reads-untracked-bytecode)."""
    skill = next(
        r["skill"]
        for r in _real_map()["rows"]
        if r["skill"] is not None and (_SKILLS_DIR / r["skill"] / "scripts").is_dir()
    )
    shutil.copytree(_SKILLS_DIR / skill, tmp_path / "skills" / skill)
    pyc = tmp_path / "skills" / skill / "scripts" / "__pycache__" / "x.cpython-312.pyc"
    pyc.parent.mkdir(exist_ok=True)
    pyc.write_bytes(b"\xa7\r\r")
    stale = f"row(skill={skill!r}): scripts hash stale"
    planted = _find_stale_hash_tuples(
        _real_map(), _law_section_bodies(), skills_dir=tmp_path / "skills"
    )
    assert not any(stale in v for v in planted), planted
    edited = sorted((tmp_path / "skills" / skill / "scripts").glob("*.py"))[0]
    edited.write_text(edited.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    violations = _find_stale_hash_tuples(
        _real_map(), _law_section_bodies(), skills_dir=tmp_path / "skills"
    )

    assert any(stale in v for v in violations), violations


@functools.cache
def _projected_specs_agents_relpath(repo_root: Path) -> str | None:
    """`specs/AGENTS.md` is a projected INSTANCE path, proven by running the real `scaffold()`
    into a scratch dir and diffing it against its generating template — never by checkout
    presence (bug citation-enforcer-resolves-projected-instance-paths-against-the-checkout)."""
    templates_dir = repo_root / "dadaia_workspace" / "public" / "templates"
    source = templates_dir / "specs-AGENTS.md"
    if not source.exists():
        return None

    from dadaia_workspace.core.workspace_layout import render_registry_tables
    from dadaia_workspace.features.specs.canon import scaffold

    with tempfile.TemporaryDirectory() as scratch:
        specs_dir = Path(scratch) / "specs"
        created = scaffold(
            specs_dir,
            project_name="citation-enforcer-projection-probe",
            force=True,
            public_dir=templates_dir.parent,
        )
        target = specs_dir / "AGENTS.md"
        rendered = render_registry_tables(source.read_text(encoding="utf-8"))  # WP-38
        if target not in created or target.read_text(encoding="utf-8") != rendered:
            return None
    return "AGENTS.md"


def _real_dead_path_citations(repo_root: Path = _REPO_ROOT) -> list[str]:
    rel = _projected_specs_agents_relpath(repo_root)
    exempt = frozenset() if rel is None else frozenset({f"specs/{rel}"})
    return dead_path_citations_in_tree(_PUBLIC, repo_root, exempt=exempt)


def test_projected_specs_agents_md_citation_survives_bare_checkout() -> None:
    """Bug citation-enforcer-resolves-projected-instance-paths-against-the-checkout: with the
    local `specs/AGENTS.md` leftover hidden (as in a bare CI clone), no citation of it is dead."""
    real_path = _REPO_ROOT / "specs" / "AGENTS.md"
    hidden_path = real_path.with_name("AGENTS.md.hidden-for-bare-checkout-test")
    moved = real_path.exists()
    if moved:
        real_path.rename(hidden_path)
    try:
        violations = _real_dead_path_citations()
    finally:
        if moved:
            hidden_path.rename(real_path)
    assert [v for v in violations if "specs/AGENTS.md" in v] == []


def _fixture_skill(tmp_path: Path, body: str) -> Path:
    skill = tmp_path / "fixture-repo" / "dadaia_workspace" / "public" / "skills" / "fixture-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    return tmp_path / "fixture-repo"


@pytest.mark.parametrize(
    ("body", "token"),
    [
        pytest.param("See `specs/this-path-does-not-exist-fixture.md`.\n", "specs/this-path-does-not-exist-fixture.md", id="9-dead-path"),
        # the lookalike of the one projected target, wrong nesting, is still dead
        pytest.param("See `specs/nested/AGENTS.md`.\n", "specs/nested/AGENTS.md", id="11-lookalike-projected-path"),
        pytest.param("Run `dadaia fixture-nonexistent-verb now`.\n", "dadaia fixture-nonexistent-verb now", id="10-dead-verb"),
    ],
)  # fmt: skip
def test_a_planted_dead_citation_turns_red(tmp_path: Path, body: str, token: str) -> None:
    """A27.20 mutation fixtures 9-11: one located violation per planted dead citation."""
    repo = _fixture_skill(tmp_path, body)
    public = repo / "dadaia_workspace" / "public"
    violations = dead_path_citations_in_tree(public, repo) + dead_verb_citations_in_tree(
        public, repo, command_paths()
    )
    assert len(violations) == 1 and token in violations[0], violations
    assert violations[0].startswith("dadaia_workspace/public/skills/fixture-skill/SKILL.md:1:")


def test_posix_relpath_is_separator_agnostic_under_windows_path_semantics() -> None:
    """Bug citation-mutation-fixtures-never-turn-red-on-windows: a `file:line` prefix built from
    Windows path semantics renders POSIX."""
    root = PureWindowsPath(r"D:\pytest-fixture-repo")
    md = root / "dadaia_workspace" / "public" / "skills" / "fixture-skill" / "SKILL.md"
    assert posix_relpath(md, root) == "dadaia_workspace/public/skills/fixture-skill/SKILL.md"


def test_mutation_fixture_12_dead_body_pointer_turns_red(tmp_path: Path) -> None:
    """A dead skill pointer, a dead section pointer and a dead scoped-rule pointer are each flagged."""
    public = tmp_path / "fixture-repo" / "dadaia_workspace" / "public"
    (public / "skills" / "dd-real").mkdir(parents=True)
    (public / "skills" / "dd-real" / "SKILL.md").write_text("## 1. When\n", encoding="utf-8")
    (public / "skills" / "dd-real" / "NOTES.md").write_text(
        "See `dd-gone`.\nSee `dd-real` §9.\nSee `nowhere-AGENTS.md`.\nSee `dd-real` §1.\n",
        encoding="utf-8",
    )

    violations = dead_body_pointers_in_tree((public / "skills",), public, tmp_path / "fixture-repo")

    assert len(violations) == 3, violations
    assert "dead skill pointer `dd-gone`" in violations[0]
    assert "dead section pointer `dd-real` §9" in violations[1]
    assert "dead scoped-rule pointer `nowhere-AGENTS.md`" in violations[2]


_LAW_ROOTS = ("dadaia_workspace/public/data", "dadaia_workspace/public/skills",
              "dadaia_workspace/public/templates", "docs")  # fmt: skip
_CITED_INVOCATION_RE = re.compile(
    r"(?<![\w.-])dadaia(?![\w.-])((?:\s+[a-z][a-z0-9-]*)*)((?:\s+[^`]*)?)"
)


def test_every_cited_dadaia_invocation_names_a_real_verb_and_option() -> None:
    """repo-law-prescribes-a-removed-install-option: every `dadaia <verb…> --option` the law
    cites resolves in the live Click tree, each `--option` among that command's parameters."""
    from typer.main import get_command

    from dadaia_workspace.cli.main import app

    root = get_command(app)
    files = [_REPO_ROOT / "AGENTS.md", _REPO_ROOT / "README.md"] + [
        md for root_dir in _LAW_ROOTS for md in sorted((_REPO_ROOT / root_dir).rglob("*.md"))
    ]
    cited = [
        (f"{posix_relpath(md, _REPO_ROOT)}:{number}", token)
        for md in files
        if md.is_file() and not md.is_symlink()
        for number, line in enumerate(md.read_text(encoding="utf-8").splitlines(), start=1)
        for token in re.findall(r"`([^`\n]+)`", line)
    ]
    violations: list[str] = []
    for where, token in cited:
        for m in _CITED_INVOCATION_RE.finditer(token):
            command: Any = root
            for word in m.group(1).split():
                sub = (getattr(command, "commands", None) or {}).get(word)
                if sub is None:
                    break  # a positional argument ends the verb path
                command = sub
            declared = {opt for param in command.params for opt in param.opts} | {"--help"}
            violations += [
                f"{where}: `{token}` — {option} is not an option"
                for option in re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", m.group(2))
                if option not in declared
            ]
    assert violations == [], "\n".join(violations)


def _leading_words(nodes: list[ast.expr]) -> tuple[str, ...]:
    words: list[str] = []
    for node in nodes:
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            break
        if node.value.startswith("-"):
            break
        words.append(node.value)
    return tuple(words)


def _self_invoked_verb_paths() -> list[tuple[str, tuple[str, ...]]]:
    """Every literal `dadaia` argv the package builds — through the `cli`/`doctor_clean`
    helpers or a list naming `dadaia_workspace.cli.main` — as ``(file:line, verb path)``."""
    found: list[tuple[str, tuple[str, ...]]] = []
    for path in sorted((_REPO_ROOT / "dadaia_workspace").rglob("*.py")):
        if path.is_symlink():
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            argvs: list[list[ast.expr]] = []
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"cli", "doctor_clean"}:
                    argvs.append(node.args)
            elif isinstance(node, ast.List):
                argvs += [
                    node.elts[i + 1 :]
                    for i, e in enumerate(node.elts)
                    if isinstance(e, ast.Constant) and e.value == "dadaia_workspace.cli.main"
                ]
            found += [(f"{rel}:{node.lineno}", w) for argv in argvs if (w := _leading_words(argv))]
    return found


def test_every_self_invoked_dadaia_verb_exists() -> None:
    """Intent: CONTRACT — 0.4.7 FR5 (T-047-78), bug `certify-invokes-a-retired-verb`: the
    longest literal prefix of every argv the package runs resolves to a LEAF verb."""
    paths = set(command_paths())
    leaves = {p for p in paths if not any(q[: len(p)] == p and len(q) > len(p) for q in paths)}
    invocations = _self_invoked_verb_paths()
    assert invocations, "the AST walk found no self-invoked dadaia argv — mis-rooted scan?"
    violations = [
        f"{where}: `dadaia {' '.join(words)}` resolves to no leaf verb"
        for where, words in invocations
        if not any(words[:n] in leaves for n in range(len(words), 0, -1))
    ]
    assert violations == [], "\n".join(violations)


_INLINE_VERB_RE = re.compile(r"\b([a-z]+)\.py ([a-z][a-z-]*)")
_LISTED_VERBS_RE = re.compile(r"\b([a-z]+)\.py` — ((?:`[a-z][^`]*`(?:, )?)+)")
_ADD_PARSER_RE = re.compile(r"add_parser\(\s*\"([a-z][a-z-]*)\"")


def test_every_cited_skill_script_verb_exists() -> None:
    """Intent: CONTRACT — bug `spec-navigator-cites-dead-memory-verb-and-false-binding-claim`:
    a verb cited after `<script>.py` — inline (`memory.py drift`) or as the backticked list that
    follows (`memory.py` — `catalog generate`, …) — is one of that script's `add_parser` names."""
    verbs: dict[str, set[str]] = {}
    for script in sorted(_PUBLIC.glob("skills/*/scripts/[a-z]*.py")):
        found = verbs.setdefault(script.stem, set())
        for source in [script, *script.parent.glob(f"_{script.stem}*.py")]:
            found.update(_ADD_PARSER_RE.findall(source.read_text(encoding="utf-8")))
    verbs = {name: found for name, found in verbs.items() if found}
    assert "catalog" in verbs.get("memory", set()), "script verb scan mis-rooted"
    violations: list[str] = []
    for md_path in sorted(_PUBLIC.rglob("*.md")):
        rel = md_path.relative_to(_REPO_ROOT).as_posix()
        for number, line in enumerate(md_path.read_text(encoding="utf-8").splitlines(), 1):
            cited = [(m.group(1), m.group(2)) for m in _INLINE_VERB_RE.finditer(line)]
            for listed in _LISTED_VERBS_RE.finditer(line):
                cited += [
                    (listed.group(1), v.split()[0])
                    for v in re.findall(r"`([^`]+)`", listed.group(2))
                ]
            violations += [
                f"{rel}:{number}: `{script}.py {verb}` is not a verb of the script"
                for script, verb in cited
                if script in verbs and verb not in verbs[script]
            ]
    assert violations == [], "\n".join(violations)
