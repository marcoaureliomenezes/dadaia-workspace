"""Intent: CONTRACT — V32, V33, V34, V35, V36; V37, V38, V39 (0.5.0 AC6.2–AC6.6); size: SMALL.

Repo-pure slop ratchets: measured at birth, pinned, ratcheting down only; every
tree walk goes through the one tracked-files enumeration the other ratchets use.
V37–V39 carry a keyed allowance (AC6.5): an unlisted hit fails, a vanished key fails
stale, a value is an OPEN bug id (or ``parity:<test>`` / ``report-only`` where stated),
and the allowance never outgrows its birth size (AC6.6).
"""

from __future__ import annotations

import ast
import io
import json
import re
import tokenize
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import pytest

from tests.helpers.suite_files import tracked_test_files

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_THIS_FILE = Path(__file__).resolve()

# ---------------------------------------------------------------------------
# V32 — governance ids in production comments and docstrings
# ---------------------------------------------------------------------------

_GOVERNANCE_ID_RE = re.compile(
    r"\b(FR[0-9]+|T-[0-9]{2,3}(-[0-9]+)?|ADR[ -]?[0-9]+|v0\.[0-9]+(\.[0-9]+)?)\b"
)
_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

# RECORDED CEILING (ratchet DOWN ONLY) — measured 2026-09-20 on this HEAD, every comment
# token plus every docstring line under dadaia_workspace/**/*.py. Lower it in the commit
# that deletes the ids; raising it is never a ratchet move.
_V32_CEILING = 646


def _governance_id_lines(source: str) -> int:
    """Comment tokens and docstring lines of *source* that carry a governance id."""
    hits = sum(
        1
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT and _GOVERNANCE_ID_RE.search(token.string)
    )
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, _DOCSTRING_OWNERS):
            docstring = ast.get_docstring(node, clean=False) or ""
            hits += sum(1 for line in docstring.splitlines() if _GOVERNANCE_ID_RE.search(line))
    return hits


def test_v32_governance_ids_in_production_comments_and_docstrings() -> None:
    """V32 — comment tokens and docstring lines under dadaia_workspace/ naming an FR, T-,
    ADR or v0.x id, pinned at the recorded ceiling. Ratchet DOWN ONLY; target 0 (tests/ are excluded)."""
    total = sum(
        _governance_id_lines(path.read_text(encoding="utf-8"))
        for path in tracked_test_files(_REPO_ROOT, "*.py", tree="dadaia_workspace")
    )
    assert total <= _V32_CEILING, (
        f"governance ids in production comments/docstrings grew to {total} "
        f"(ceiling {_V32_CEILING}). The what, the history and any spec, task, ADR or "
        "version id live in git and the ledgers — delete the id, never raise the ceiling."
    )

    # Mutation fixture — a clean module counts 0; one docstring line and one comment
    # carrying an id count 2.
    clean = 'X = 1  # the non-obvious why\n\n\ndef f() -> None:\n    """Contract."""\n'
    assert _governance_id_lines(clean) == 0
    violating = '"""Entrypoint (FR99, T-000-00)."""\nX = 1  # see ADR 0000\n'
    assert _governance_id_lines(violating) == 2


# ---------------------------------------------------------------------------
# V33 — PREFIX-NN families without a mechanical reader
# ---------------------------------------------------------------------------

_FAMILY_TOKEN_RE = re.compile(r"\b[A-Z]{1,4}-?[0-9]{2,3}\b")
_UPPER_RUN_RE = re.compile(r"[A-Z]+")
_WORD_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
_V33_TOKEN_TREES = ("specs", "dadaia_workspace", "tests")
_V33_READER_TREES = ("dadaia_workspace", "tests")
_V33_RATIFIED_FAMILIES = frozenset({"FR", "AC", "T"})

# RECORDED CEILING (ratchet DOWN ONLY) — measured 2026-09-20 on this HEAD; the failing
# assertion prints the orphan family list so the number is reproducible.
_V33_CEILING = 35


def _family_witnesses(texts: Iterable[str]) -> dict[str, set[tuple[str, int]]]:
    """Each family prefix mapped to the words its tokens sit in and the prefix offset."""
    families: dict[str, set[tuple[str, int]]] = {}
    for text in texts:
        for match in _FAMILY_TOKEN_RE.finditer(text):
            left, right = match.start(), match.end()
            while left > 0 and text[left - 1] in _WORD_CHARS:
                left -= 1
            while right < len(text) and text[right] in _WORD_CHARS:
                right += 1
            prefix = _UPPER_RUN_RE.match(match.group(0))
            assert prefix is not None
            families.setdefault(prefix.group(0), set()).add(
                (text[left:right], match.start() - left)
            )
    return families


def _string_constants(source: str) -> list[str]:
    """Every non-empty string constant in *source* that is not a bare docstring statement."""
    tree = ast.parse(source)
    bare = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value
        and id(node) not in bare
    ]


def _reads_family(constant: str, prefix: str, witnesses: Iterable[tuple[str, int]]) -> bool:
    """*constant* (a regex, else a literal) matches a witness through its prefix and beyond."""
    try:
        pattern = re.compile(constant)
    except re.error:
        pattern = re.compile(re.escape(constant))
    return any(
        (match := pattern.search(word)) is not None
        and match.start() <= offset
        and match.end() > offset + len(prefix)
        for word, offset in witnesses
    )


def _orphan_families(texts: Iterable[str], constants: Iterable[str]) -> list[str]:
    """Family prefixes found in *texts* that no constant in *constants* reads."""
    readers: dict[str, list[str]] = {}
    for constant in constants:
        for run in set(_UPPER_RUN_RE.findall(constant)):
            readers.setdefault(run, []).append(constant)
    return sorted(
        prefix
        for prefix, witnesses in _family_witnesses(texts).items()
        if prefix not in _V33_RATIFIED_FAMILIES
        and not any(_reads_family(c, prefix, witnesses) for c in readers.get(prefix, ()))
    )


def _tracked_texts(tree: str, pattern: str) -> Iterable[str]:
    for path in tracked_test_files(_REPO_ROOT, pattern, tree=tree):
        if "_archive" in path.relative_to(_REPO_ROOT).parts or path == _THIS_FILE:
            continue
        try:
            yield path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def test_v33_prefix_families_without_a_mechanical_reader() -> None:
    """V33 — distinct `PREFIX-NN` families over specs/ (minus _archive/), dadaia_workspace/
    and tests/ that no regex or string constant in the source trees reads. DOWN ONLY."""
    texts = [text for tree in _V33_TOKEN_TREES for text in _tracked_texts(tree, "*")]
    constants = [
        constant
        for tree in _V33_READER_TREES
        for source in _tracked_texts(tree, "*.py")
        for constant in _string_constants(source)
    ]
    orphans = _orphan_families(texts, constants)
    assert len(orphans) <= _V33_CEILING, (
        f"{len(orphans)} PREFIX-NN families have no mechanical reader (ceiling "
        f"{_V33_CEILING}). A concept takes a glossary name; a numbered code exists only "
        f"where a mechanical index reads it. Orphan families: {orphans}"
    )

    # Mutation fixture — upper-cased at runtime so the fixture never enters the scan
    # itself: one read family, one orphan; dropping the reader makes both orphans.
    corpus = ["foo-01 has a reader, bar-02 has none".upper()]
    assert _orphan_families(corpus, ["foo-".upper()]) == ["BAR"]
    assert _orphan_families(corpus, []) == ["BAR", "FOO"]


# ---------------------------------------------------------------------------
# V36 — the skill-script corpus: files and total Python lines
# ---------------------------------------------------------------------------

# RECORDED PINS (ratchet DOWN ONLY) — measured on the post-candidate corpus: every
# tracked `*.py` under dadaia_workspace/public/skills/*/scripts/. A ledger's writer moved
# out of the CLI ONCE; a growing corpus after that is CLI code re-typed, not code moved.
# T-047-94 re-pin (down only, never raised again this candidate): the atom generator and
# the second frontmatter validator are gone and the index renderer folded into the catalog
# one — 31 -> 29 files, 3,657 -> 3,436 lines measured. The ceiling below is that measurement
# plus the budget the SPEC already authorized for the drift verb and the `release.py memory`
# verb (+1 file; +85 + 14 + 16 + 50 + 6 = +171 lines), so no later task in this candidate may
# raise it; T-047-105 re-pinned it to the measured post-candidate value (30 files, 3,618 lines).
_V36_FILE_CEILING = 30
_V36_LINE_CEILING = 3618


def _skill_scripts() -> list[Path]:
    return [
        path
        for path in tracked_test_files(_REPO_ROOT, "*.py", tree="dadaia_workspace")
        if "public/skills/" in path.as_posix() and "/scripts/" in path.as_posix()
    ]


def test_v36_skill_script_corpus_is_pinned() -> None:
    """V36 — at most 30 skill-script files and 3,618 total lines of skill Python. The
    ledger writers moved out of the CLI once: growth here is a verb regrown, never moved."""
    scripts = _skill_scripts()
    assert len(scripts) <= _V36_FILE_CEILING, (
        f"skill-script files grew to {len(scripts)} (ceiling {_V36_FILE_CEILING}). A new "
        "file earns its place by a verb leaving the CLI, never by restating one."
    )
    total = _skill_corpus_lines(scripts)
    assert total <= _V36_LINE_CEILING, (
        f"skill Python grew to {total} lines (ceiling {_V36_LINE_CEILING}). Delete the "
        "duplicated helper — never raise the ceiling."
    )

    # Mutation fixture — the counter reads real files, and an empty set counts 0.
    assert _skill_corpus_lines([]) == 0
    assert scripts, "the skill-script corpus must not be empty"


# ---------------------------------------------------------------------------
# V34 — bytes of the live candidate's SPEC.md and TASKS.md
# ---------------------------------------------------------------------------

_V34_CEILINGS = {"SPEC.md": 24 * 1024, "TASKS.md": 12 * 1024}


def _live_release_dir() -> Path | None:
    """The one non-archived `specs/releases/<id>/` carrying a `_RELEASE.json`, or
    ``None`` in the post-ship window (folder archived, next release not yet defined) —
    at most one live release ever (ADR 0005), never necessarily one."""
    releases = _REPO_ROOT / "specs" / "releases"
    live = [
        path.parent
        for path in tracked_test_files(_REPO_ROOT, "_RELEASE.json", tree="specs/releases")
        if path.parent.parent == releases
    ]
    assert len(live) <= 1, f"at most one live release expected, found {live}"
    return live[0] if live else None


def _byte_ceiling_violations(sizes: dict[str, int]) -> list[str]:
    return [
        f"{name}: {size} B > {_V34_CEILINGS[name]} B"
        for name, size in sizes.items()
        if size > _V34_CEILINGS[name]
    ]


def test_v34_live_candidate_trio_bytes_under_the_fixed_ceiling() -> None:
    """V34 — the live candidate's SPEC.md is at most 24 KB and its TASKS.md at most 12 KB;
    a fixed ceiling, never a pin."""
    live = _live_release_dir()
    if live is not None:
        # A candidate in DEFINITION may hold only its SPEC.md at the root (rc-archive
        # ran, PLAN/TASKS not yet authored): measure what exists, never demand the trio.
        # Content bytes, LF-normalised: a CRLF checkout must not move a ratchet.
        sizes = {
            name: len((live / name).read_bytes().replace(b"\r\n", b"\n"))
            for name in _V34_CEILINGS
            if (live / name).is_file()
        }
        assert _byte_ceiling_violations(sizes) == [], (
            f"{live.name} trio exceeds the byte ceiling — above it the scope is open "
            "enough to be two candidates."
        )

    # Mutation fixture — one byte over either ceiling is a violation.
    assert _byte_ceiling_violations({"SPEC.md": 24 * 1024 + 1, "TASKS.md": 12 * 1024}) == [
        "SPEC.md: 24577 B > 24576 B"
    ]


# ---------------------------------------------------------------------------
# V35 — the skill corpus: directories and total Markdown lines
# ---------------------------------------------------------------------------

# RECORDED PINS (ratchet DOWN ONLY) — measured on the post-candidate corpus: every
# tracked `*.md` under dadaia_workspace/public/skills/. Re-pinned at every closure that
# touches the corpus, downward only; raising either is never a ratchet move.
_V35_DIR_CEILING = 18
_V35_LINE_CEILING = 2863


def _skill_corpus_markdown() -> list[Path]:
    return [
        path
        for path in tracked_test_files(_REPO_ROOT, "*.md", tree="dadaia_workspace")
        if "public/skills/" in path.as_posix()
    ]


def _skill_corpus_lines(paths: Iterable[Path]) -> int:
    return sum(len(path.read_text(encoding="utf-8").splitlines()) for path in paths)


def test_v35_skill_corpus_is_pinned() -> None:
    """V35 — at most 18 skill directories and 2,863 total lines of skill Markdown.
    A rule lives in one home: a growing corpus is a rule restated, not a rule added."""
    corpus = _skill_corpus_markdown()
    dirs = {
        path.relative_to(_REPO_ROOT / "dadaia_workspace" / "public" / "skills").parts[0]
        for path in corpus
    }
    assert len(dirs) <= _V35_DIR_CEILING, (
        f"skill directories grew to {len(dirs)} (ceiling {_V35_DIR_CEILING}). A new "
        "skill earns its dir by deleting another's material, never by restating it."
    )
    total = _skill_corpus_lines(corpus)
    assert total <= _V35_LINE_CEILING, (
        f"skill Markdown grew to {total} lines (ceiling {_V35_LINE_CEILING}). Find the "
        "statement's other home and delete the copy — never raise the ceiling."
    )

    # Mutation fixture — the counter reads real files, and an empty set counts 0.
    assert _skill_corpus_lines([]) == 0
    assert _skill_corpus_lines([_THIS_FILE]) > 0


# ---------------------------------------------------------------------------
# V37–V39 — one authority per fact, per deleter, per doctor fix (AC6.2–AC6.6)
# ---------------------------------------------------------------------------

_PACKAGE = _REPO_ROOT / "dadaia_workspace"
_SWEEP = "features/spec_context/sweep.py"


def _package_sources() -> dict[str, str]:
    """Every tracked module, skill script and hook, keyed by its package-relative path."""
    return {
        path.relative_to(_PACKAGE).as_posix(): path.read_text(encoding="utf-8")
        for path in tracked_test_files(_REPO_ROOT, "*.py", tree="dadaia_workspace")
    }


def _open_bug_ids() -> set[str]:
    ledger = _REPO_ROOT / "specs" / "bugs" / "BUGS.jsonl"
    records = (json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines())
    return {record["id"] for record in records if record.get("status") == "open"}


def _allowance_violations(
    hits: set[str], allowance: dict[str, str], *, birth: int, also: frozenset[str] = frozenset()
) -> list[str]:
    """AC6.5/AC6.6: unlisted hits, stale keys, values that are no open bug id, and an
    allowance grown past its birth size — each one line, empty when the ratchet holds."""
    open_bugs = _open_bug_ids()
    problems = [f"unlisted: {hit}" for hit in sorted(hits - allowance.keys())]
    problems += [f"stale key (delete it): {key}" for key in sorted(allowance.keys() - hits)]
    problems += [
        f"{key} -> {value!r} is neither an open bug id nor an allowed value"
        for key, value in sorted(allowance.items())
        if value not in open_bugs and value not in also and not value.startswith("parity:")
    ]
    for key, value in sorted(allowance.items()):
        if (
            value.startswith("parity:")
            and not (_REPO_ROOT / value.removeprefix("parity:")).is_file()
        ):
            problems.append(f"{key} -> {value!r} names no test file")
    if len(allowance) > birth:
        problems.append(f"allowance grew to {len(allowance)} (birth {birth}) — it only shrinks")
    return problems


def _definition(node: ast.stmt) -> tuple[str, str] | None:
    """``(name, shape)`` of a top-level function (docstring dropped) or UPPER constant
    whose value is not a bare scalar literal; ``None`` for anything else."""
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        body = node.body[1:] if ast.get_docstring(node) is not None else node.body
        return node.name, ast.dump(node.args) + ast.dump(ast.Module(body=body, type_ignores=[]))
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target: ast.expr | None = node.targets[0]
    else:
        target = node.target if isinstance(node, ast.AnnAssign) else None
    value = getattr(node, "value", None)
    if not isinstance(target, ast.Name) or value is None or isinstance(value, ast.Constant):
        return None
    return (target.id, ast.dump(value)) if target.id.lstrip("_").isupper() else None


def _duplicate_definitions(sources: dict[str, str]) -> set[str]:
    """``file:symbol`` for every top-level definition AST-identical in two or more files."""
    homes: dict[tuple[str, str], set[str]] = defaultdict(set)
    for rel, text in sources.items():
        for node in ast.parse(text).body:
            if (found := _definition(node)) is not None:
                homes[found].add(rel)
    return {f"{rel}:{name}" for (name, _), rels in homes.items() if len(rels) > 1 for rel in rels}


#: V37 allowance, born 2026-09-27 at 65: each duplicate, keyed to the open bug deleting it.
_V37_BIRTH = 65
_V37_ALLOWANCE: dict[str, str] = {
}


def test_v37_one_home_per_definition() -> None:
    """V37 — a function or non-scalar UPPER constant defined identically in two modules,
    skill scripts or hooks is a second authority (folds test_required_evidence_has_one_home)."""
    problems = _allowance_violations(
        _duplicate_definitions(_package_sources()), _V37_ALLOWANCE, birth=_V37_BIRTH
    )
    assert problems == [], "\n".join(problems)


def test_v37_trips_on_a_planted_second_authority() -> None:
    """RED fixture: a regex and a helper copied into a second module are flagged; a bare
    scalar and a same-name different body are not."""
    first = "import re\n_ID_RE = re.compile('x')\nKIND = 'a'\ndef load(p):\n    return p\n"
    second = "import re\n_ID_RE = re.compile('x')\nKIND = 'a'\ndef load(p):\n    return 1\n"
    assert _duplicate_definitions({"a.py": first, "b.py": second}) == {"a.py:_ID_RE", "b.py:_ID_RE"}


_DELETES = frozenset({"rmtree", "unlink", "rmdir", "removedirs"})
_OS_DELETES = frozenset({"remove", "move"})


def _destructive_calls(sources: dict[str, str]) -> set[str]:
    """``file:function`` for every delete call outside the one deleter (``sweep``)."""
    hits: set[str] = set()
    for rel, text in sources.items():
        if rel == _SWEEP:
            continue
        tree = ast.parse(text)
        owner: dict[int, str] = {}
        functions = [
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        ]
        for function in sorted(functions, key=lambda f: f.lineno):
            owner.update({id(node): function.name for node in ast.walk(function)})
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                base, attr = ast.unparse(node.func.value), node.func.attr
                if (attr in _DELETES and base != "sweep") or (
                    attr in _OS_DELETES and base in {"os", "shutil"}
                ):
                    hits.add(f"{rel}:{owner.get(id(node), '<module>')}")
    return hits


#: V38 allowance, born 2026-09-27 at 16. The install-ledger prune is PLAN §1.1's
#: "who owns an entry under a harness dir" authority (`_reconcile_install_ledger`). Certify
#: deletes its own disposable run; reconcile's rollback restores a state file to absent.
_V38_BIRTH = 16
_V38_ALLOWANCE: dict[str, str] = {
    # a failed swap never leaves its temp sibling — pinned by each writer's own test
    "core/atomic_write.py:atomic_write": "parity:tests/unit/core/test_atomic_write.py",
    "public/skills/dd-bug-resolution/scripts/_ledger.py:replace": "parity:tests/unit/skills/test_ledger_write_verbs_refuse_with_the_pair_intact.py",
    "features/certification/service.py:certify": "parity:tests/integration/features/certification/test_certify_journey.py",
    # the v1 hop drops the retired primary_context.json — pinned by the B7 transform test
    "features/migrate/state_v2.py:execute_migration": "parity:tests/unit/features/migrate/test_state_v2.py",
    "features/reconcile/service.py:_restore_state": "parity:tests/unit/features/reconcile/test_reconcile_service.py",
    # re-verified exact-token delete of a template artifact; features/specs cannot import sweep
    "features/specs/doctor_memory.py:fix_placeholder_atom": "parity:tests/unit/features/specs/test_scaffold_placeholder_repair.py",
    "infrastructure/projection.py:_clear": "parity:tests/integration/test_install_ledger_reconciliation.py",
    "infrastructure/public_assets.py:_prune_empty_dirs": "parity:tests/integration/test_install_ledger_reconciliation.py",
    "infrastructure/public_assets.py:_reconcile_install_ledger": "parity:tests/integration/test_install_ledger_reconciliation.py",
    "infrastructure/public_assets.py:stage": "parity:tests/integration/test_staged_assets_have_consumers.py",
    # `new` is all-or-nothing and drops a closed candidate's PLAN/TASKS (stacked-candidate law)
    "public/skills/dd-release-implementation/scripts/_release_new.py:new_release": "parity:tests/unit/skills/test_release_implementation_release_script.py",
    # `ship` removes the shipped release dir (git is the archive) — B25-1's own Then
    "public/skills/dd-release-implementation/scripts/release.py:_ship": "parity:tests/unit/skills/test_release_implementation_release_script.py",
}


def test_v38_deletes_live_in_the_one_deleter() -> None:
    """V38 — a delete call (``rmtree unlink rmdir removedirs``, ``os.remove``,
    ``shutil.move``) outside ``features/spec_context/sweep.py`` is a second deleter."""
    problems = _allowance_violations(
        _destructive_calls(_package_sources()), _V38_ALLOWANCE, birth=_V38_BIRTH
    )
    assert problems == [], "\n".join(problems)


def test_v38_trips_on_a_planted_deleter() -> None:
    """RED fixture: an unlink in a new module is flagged; sweep's own calls are not."""
    stray = "from pathlib import Path\ndef tidy(p):\n    Path(p).unlink()\n"
    sources = {
        "features/x/tidy.py": stray,
        _SWEEP: stray,
        "ok.py": "import os\nos.replace('a', 'b')\n",
    }
    assert _destructive_calls(sources) == {"features/x/tidy.py:tidy"}


def test_no_doctor_section_subset_outside_doctor() -> None:
    """sa-reconcile-certify-skip-the-workspace-walk#B5: no code selects a subset of doctor
    sections — no `[...]["sections"]` read, no literal naming two section names."""
    names = {"workspace", "specs", "ledgers"}
    hits = [
        f"{rel}:{node.lineno}"
        for rel, text in _package_sources().items()
        for node in ast.walk(ast.parse(text))
        if (isinstance(node, ast.Subscript) and ast.unparse(node.slice) == "'sections'")
        or (
            isinstance(node, ast.Tuple | ast.List | ast.Set)
            and len(names & {ast.unparse(e).strip("'") for e in node.elts}) >= 2
        )
    ]
    assert hits == []


def _doctor_codes() -> set[str]:
    """Every code any doctor emits: the three rule tables, the ledger scripts, onboarding."""
    from dadaia_workspace.features.backlog.doctor import RULES as BACKLOG_RULES
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES
    from dadaia_workspace.features.workspace import onboarding
    from dadaia_workspace.infrastructure.ledger_scripts import LEDGER_SCRIPTS

    rules = [*SPECS_RULES, *BACKLOG_RULES, *workspace_rules(expired_only=False, context=None)]
    return (
        {code for rule in rules for code in rule.codes}
        | {script.code for script in LEDGER_SCRIPTS}
        | {onboarding.CODE}
    )


#: V39 allowance, born 2026-09-27 at 52: a code with no fix-clears case in
#: tests/integration/test_doctor_fix_lines_clear_their_finding.py; a code carrying a fix
#: is keyed to the bug that says its fix may not clear, one with none is `report-only`.
_V39_BIRTH = 52
_V39_ALLOWANCE: dict[str, str] = {
    "ONBOARDING": "parity:tests/integration/test_onboarding_steps_property.py",
    "WS-INVARIANT": "parity:tests/integration/test_unfixable_findings_carry_their_own_fix.py",
}


def _uncovered(codes: set[str], planted: set[str]) -> set[str]:
    return codes - planted


def test_v39_every_doctor_code_has_a_fix_clears_case_or_a_key() -> None:
    """V39 — every doctor code has a fix-clears case, or an allowance key."""
    from tests.integration.test_doctor_fix_lines_clear_their_finding import (
        OPERATOR_ACTION,
        PLANTS,
        REPORT_ONLY,
    )
    from tests.integration.test_workspace_fix_lines_clear_their_finding import WORKSPACE_PLANTS

    # A code is covered by its fix-clears plant, or by the proof test of its table.
    covered = set(PLANTS) | set(REPORT_ONLY) | set(OPERATOR_ACTION) | set(WORKSPACE_PLANTS)
    problems = _allowance_violations(
        _uncovered(_doctor_codes(), covered),
        _V39_ALLOWANCE,
        birth=_V39_BIRTH,
        also=frozenset({"report-only"}),
    )
    assert problems == [], "\n".join(problems)


def test_v39_trips_on_an_unlisted_code() -> None:
    """RED fixture: a code with neither a plant nor a key is reported unlisted."""
    problems = _allowance_violations(_uncovered({"ZZ-NEW-1", "ZZ-OK-1"}, {"ZZ-OK-1"}), {}, birth=0)
    assert problems == ["unlisted: ZZ-NEW-1"]
