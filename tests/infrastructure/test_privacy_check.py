"""Public-source hygiene contract: no bytecode leaks into the canonical public asset tree.

Two failure modes stay closed:

1. **At rest.** No ``__pycache__``/``.pyc`` sits under ``dadaia_workspace/public/``.

2. **Packaging.** The built wheel/sdist contains no ``.pyc``. ``poetry-core`` honours the
   ``[tool.poetry] exclude`` globs for both artifacts; this test asserts the exclusion config
   is present (no full build invocation).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tomllib
from collections.abc import Collection
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.privacy_check import (
    PORTUGUESE_CONTROL_TERMS,
    load_privacy_terms,
)
from tests.fixtures.real_git import git
from tests.helpers.oslib import Undecodable, read_text, run, write_text
from tests.helpers.privacy_fixtures import internal_host, private_ip
from tests.helpers.scan_population import assert_populated
from tests.helpers.suite_files import tracked

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_ROOT = _REPO_ROOT / "dadaia_workspace" / "public"
_SCRIPTS_DIR = _PUBLIC_ROOT / "scripts"


def tracked_bytecode(repo_root: Path) -> list[str]:
    """The bytecode artifacts *git tracks* under ``dadaia_workspace/public/`` in the repo at
    *repo_root* (sorted paths relative to it). An ignored or untracked cache is not shipped."""
    tracked_paths = (
        p.relative_to(repo_root).as_posix() for p in tracked(repo_root, "dadaia_workspace/public")
    )
    return sorted(p for p in tracked_paths if p.endswith(".pyc") or "__pycache__/" in p)


def test_bytecode_contract_judges_tracked_files_not_the_working_tree(tmp_path: Path) -> None:
    """An ignored ``__pycache__/x.pyc`` under public/ keeps the contract green; once tracked it
    fails it."""
    git(tmp_path, "init", "-q")
    cache = tmp_path / "dadaia_workspace" / "public" / "scripts" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "x.pyc").write_bytes(b"\x00")
    write_text(tmp_path / ".gitignore", "__pycache__/\n")
    assert tracked_bytecode(tmp_path) == []

    git(tmp_path, "add", "-f", str(cache / "x.pyc"))
    assert tracked_bytecode(tmp_path) == ["dadaia_workspace/public/scripts/__pycache__/x.pyc"]


def test_pre_push_ci_gate_ships_pyproject_excludes_bytecode_and_scripts_leave_no_pycache() -> None:
    """`pre-push-ci-gate.sh` is in the public/scripts/ listing, the poetry-core build config
    excludes __pycache__/*.pyc from sdist and wheel, and the canonical public asset tree
    carries no bytecode at rest.
    """
    listing = {p.name for p in _SCRIPTS_DIR.iterdir()}
    assert_populated(listing, sentinel="pre-push-ci-gate.sh")

    pyproject = _REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(read_text(pyproject))
    exclude = data["tool"]["poetry"].get("exclude", [])
    assert "**/__pycache__" in exclude
    assert "**/*.pyc" in exclude

    assert tracked_bytecode(_REPO_ROOT) == []


_PKG = _REPO_ROOT / "dadaia_workspace"
_ALL, _MD_JSON = ("public/**/*",), ("public/**/*.md", "public/**/*.json")
_PT_TERMS = "|".join(re.escape(term) for term, _ in PORTUGUESE_CONTROL_TERMS)
_OLD_PERSONAS = "|".join(("product-engineer", "software-engineer", "code-reviewer"))


def _denied_lines(globs: tuple[str, ...], pattern: str, spare: str | None) -> list[str]:
    rx = re.compile(pattern)
    paths = sorted(
        {p for g in globs for p in _PKG.glob(g) if p.is_file() and p.suffix not in {".pyc", ".png"}}
    )
    assert_populated(paths, sentinel=paths[0] if paths else _PKG / "missing")
    hits = []
    for path in paths:
        try:
            lines = read_text(path).splitlines()
        except Undecodable:
            continue
        rel = path.relative_to(_PKG).as_posix()
        hits += [
            f"{rel}:{n}: {line.strip()[:100]}"
            for n, line in enumerate(lines, 1)
            if rx.search(line) and not (spare and spare in line)
        ]
    return hits


@pytest.mark.parametrize(
    ("globs", "pattern", "spare"),
    [
        # retired surfaces staged verbatim must not be taught
        pytest.param(_ALL, r"academy|dadaia clean|tmp gc|reports cleanup|ROOT-4|legacy-quarantine|repos catalog", None, id="retired-surface"),
        # the published surface is 100% English
        pytest.param(("public/**/*.md", "public/**/*.json", "public/**/*.py", "public/**/*.txt", "public/**/*.j2", "features/specs/canon.py"), rf"(?i){_PT_TERMS}", None, id="portuguese-control-vocabulary"),
        # a retired bug-record key is not named as a live field (its retirement line is spared)
        pytest.param(_MD_JSON, r"lineage_source|registration_commit|registration_granularity|resolved_commit|resolution_granularity|root_cause|migration_note", "retired", id="retired-bug-record-key"),
        # the handoff schema admits APPROVED/REJECTED only
        pytest.param(_MD_JSON, r"REQUEST_CHANGES|\bAPPROVE\b", None, id="retired-verdict-token"),
        # shipped text teaches no Part 1 / Part 2 memory vocabulary
        pytest.param(tuple(f"public/**/*{s}" for s in (".md", ".json", ".py", ".toml", ".txt", ".sh")), r"Part 1|Part 2", None, id="memory-part-1-part-2"),
        # retired persona names, where not dd- prefixed
        pytest.param(_ALL, rf"(?<![\w-])({_OLD_PERSONAS})\b", None, id="retired-persona-name"),
        # the roster keeps no coordinator persona while the main thread coordinates
        pytest.param(("**/*",), r"project-manager", None, id="deleted-coordinator-persona"),
        # no skill prescribes the library's release tooling
        pytest.param(("public/skills/**/*.md",), r"(?i)release-please|gh pr create|last tag \+ 1", None, id="skill-release-tooling"),
        # scaffolded law cites no library ratchet, test or path
        pytest.param(("public/scaffold/**/*.md", "public/data/fixed/*.md"), r"ratchet V\d|test_\w+\.py|dadaia_workspace/|release-please", None, id="scaffold-law-library-fact"),
        # ADDITIVE is the gate's path class only
        pytest.param(("public/agents/*.md",), r"ADDITIVE", None, id="persona-additive"),
        # the bug schema cites no retired verb
        pytest.param(("public/skills/dd-bug-resolution/scripts/schemas/bug-record-v1.schema.json",), r"dadaia bugs append|features/specs/schemas\.py", None, id="bug-schema-retired-verb"),
        # the reaper's expired-only hold spares slop
        pytest.param(("public/skills/dd-cli-library/SKILL.md",), r"without touching slop", None, id="expired-only-spares-slop"),
    ],
)  # fmt: skip
def test_public_source_names_no_retired_surface(
    globs: tuple[str, ...], pattern: str, spare: str | None
) -> None:
    """Each row: shipped text an agent obeys never teaches a retired or library-only fact."""
    assert _denied_lines(globs, pattern, spare) == []


_PRIVATE_PIPELINE = (
    r"(?i)\bci[_ -]?(green|matrix|run|status)\b|green ci|watch ci|github\.com|\bgh (pr|run|api)\b"
    r'|"gh"|dependabot|codeql|pip-audit|\bpoetry\b|\bmypy\b|\bruff\b|xfail|workflow_dispatch'
    r"|self-hosted"
)


def test_public_law_names_no_private_pipeline() -> None:
    """Shipped text names no remote CI or one-stack tool."""
    globs = tuple(f"public/**/*.{s}" for s in ("md", "json", "py", "sh")) + (
        "features/chokepoints/*.py",
    )
    assert _denied_lines(globs, _PRIVATE_PIPELINE, '"exclude_paths"') == []


def test_public_law_names_no_adr_number_or_library_path() -> None:
    """Text agents read and scripts they run cite no ADR number and no library path."""
    globs = ("public/**/*",)
    assert _denied_lines(globs, r"ADR \d{4}|dadaia_workspace/", _BANNER_SPAN[0]) == []


_BARE_CLI_RE = re.compile(r"(?<![\w./-])dadaia(?:-workspace)?(?= [a-z-])")
_UVX_INIT_RE = re.compile(r"uvx dadaia-workspace(?:@\S+)? init\b")
_VENV_CALL_RE = re.compile(r"\.dadaia/\.venv/bin/dadaia((?: [a-z][\w-]*)+)([^`]*)")
_FLAG_RE = re.compile(r"(?<![\w-])--[a-z][\w-]*")
# The provenance banner is a fixed literal `infrastructure/workspace_guardrail.py` matches
# byte-for-byte to recognise a projected AGENTS.md; rewording it orphans every projection.
_BANNER_SPAN = ("dadaia_workspace/public/data/AGENTS.md", 2)


def _code_spans(text: str) -> list[tuple[int, str]]:
    """Lines inside fences and inline backtick spans — what a reader copies."""
    spans: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            fenced = not fenced
        elif fenced:
            spans.append((number, line))
        else:
            spans.extend((number, span) for span in re.findall(r"`([^`]+)`", line))
    return spans


def _bare_invocations(span: str) -> list[str]:
    return _BARE_CLI_RE.findall(_UVX_INIT_RE.sub("", span))


def _shipped_text() -> list[Path]:
    return sorted(
        {
            *_PUBLIC_ROOT.rglob("*.md"),
            *_PUBLIC_ROOT.rglob("*.txt"),
            *_PUBLIC_ROOT.rglob("*.json"),
            *(_REPO_ROOT / "docs").glob("*.md"),
            *(_REPO_ROOT / name for name in ("README.md", "llms.txt", "CONTEXT.md")),
        }
    )


def test_all_shipped_text_invokes_the_cli_by_its_venv_path() -> None:
    """The venv-guard gate blocks a bare `dadaia`, so no copyable span in shipped text may spell
    one. Zero tolerance."""
    paths = _shipped_text()
    assert_populated([p.name for p in paths], "CONTEXT.md")
    violations = [
        f"{name}:{n}: `{span.strip()}`"
        for path in paths
        for name in [path.relative_to(_REPO_ROOT).as_posix()]
        for n, span in _code_spans(read_text(path))
        if _bare_invocations(span) and (name, n) != _BANNER_SPAN
    ]
    assert violations == [], "\n".join(violations)


def test_the_bare_cli_detector_spares_the_venv_path_and_uvx_init() -> None:
    assert _bare_invocations("dadaia doctor --fix") == ["dadaia"]
    assert _bare_invocations("run dadaia-workspace init x") == ["dadaia-workspace"]
    assert _bare_invocations("/w/.dadaia/.venv/bin/dadaia context list") == []
    assert _bare_invocations("uvx dadaia-workspace init demo") == []


def _cli_tree() -> dict[str, set[str]]:
    """Every command path (`context bind`) mapped to the long flags it accepts."""
    from typer.main import get_command

    from dadaia_workspace.cli.main import app

    tree: dict[str, set[str]] = {}

    def walk(cmd: object, path: str) -> None:
        opts = {o for p in getattr(cmd, "params", []) for o in getattr(p, "opts", [])}
        tree[path] = {o for o in opts if o.startswith("--")} | {"--help"}
        for name, sub in (getattr(cmd, "commands", {}) or {}).items():
            walk(sub, f"{path} {name}".strip())

    walk(get_command(app), "")
    return tree


def _dead_flags(span: str, tree: dict[str, set[str]]) -> list[str]:
    match = _VENV_CALL_RE.search(span)
    if match is None:
        return []
    path = ""
    for word in match.group(1).split():
        if f"{path} {word}".strip() not in tree:
            break
        path = f"{path} {word}".strip()
    return [f for f in _FLAG_RE.findall(match.group(0)) if f not in tree[path]]


def test_every_flag_cited_beside_a_venv_call_exists_in_that_verbs_help() -> None:
    """A flag cited next to `.dadaia/.venv/bin/dadaia <verb>` in shipped text is one that verb
    takes."""
    tree = _cli_tree()
    violations = [
        f"{path.relative_to(_REPO_ROOT).as_posix()}:{n}: {dead}"
        for path in _shipped_text()
        for n, span in _code_spans(read_text(path))
        for dead in _dead_flags(span, tree)
    ]
    assert violations == [], "\n".join(violations)


_RETIRED_PERSONA = "dd-" + "software-engineer"


def _persona_hits(root: Path) -> list[str]:
    paths = tracked(root, "dadaia_workspace", "tests")
    assert_populated(
        paths, sentinel=root / "tests/test_a.py" if root != _REPO_ROOT else Path(__file__)
    )
    hits = []
    for path in paths:
        try:
            lines = read_text(path).splitlines()
        except Undecodable:
            continue
        rel = path.relative_to(root).as_posix()
        hits += [f"{rel}:{n}" for n, line in enumerate(lines, 1) if _RETIRED_PERSONA in line]
    return hits


def test_the_retired_persona_name_stays_out_of_library_and_tests() -> None:
    """No text file under dadaia_workspace/ or tests/ names the retired persona."""
    assert _persona_hits(_REPO_ROOT) == []


def test_the_persona_scan_survives_an_untracked_scratch_file_deleted_mid_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(tmp_path, "init", "-q")
    (tmp_path / "tests/tmp/persona-race").mkdir(parents=True)
    write_text(tmp_path / "tests" / "test_a.py", f"X = '{_RETIRED_PERSONA}'\n")
    git(tmp_path, "add", "tests/test_a.py")
    scratch = tmp_path / "tests" / "tmp" / "persona-race"
    write_text(scratch / "test_gone.py", f"X = '{_RETIRED_PERSONA}'\n")
    listed = assert_populated

    def populated_then_deleted(population: Collection[Path], sentinel: Path) -> None:
        listed(population, sentinel)
        shutil.rmtree(scratch)

    monkeypatch.setattr(sys.modules[__name__], "assert_populated", populated_then_deleted)
    assert _persona_hits(tmp_path) == ["tests/test_a.py:1"]


def test_a_public_file_that_is_not_utf8_is_skipped_by_the_scan(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.doctor_report import DoctorStatus
    from dadaia_workspace.infrastructure.privacy_check import check_public_privacy

    public = tmp_path / "lib" / "dadaia_workspace" / "public"
    public.mkdir(parents=True)
    (public / "latin.md").write_bytes(b"caf\xe9\n")

    lines = check_public_privacy(public, lambda d: d.iterdir())

    assert [line.status for line in lines] == [DoctorStatus.OK]


def test_a_denied_line_scan_skips_a_file_that_is_not_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "latin.md").write_bytes(b"secret caf\xe9\n")
    write_text(tmp_path / "plain.md", "secret\n")
    monkeypatch.setattr(sys.modules[__name__], "_PKG", tmp_path)

    assert _denied_lines(("*.md",), "secret", None) == ["plain.md:1: secret"]


def test_the_retired_persona_scan_skips_a_tracked_file_that_is_not_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "dadaia_workspace").mkdir()
    (tmp_path / "dadaia_workspace" / "latin.md").write_bytes(b"caf\xe9\n")
    write_text(tmp_path / "dadaia_workspace" / "plain.md", "fine\n")
    run(["git", "-C", str(tmp_path), "add", "."], check=True)
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "__file__", str(tmp_path / "dadaia_workspace" / "plain.md"))

    test_the_retired_persona_name_stays_out_of_library_and_tests()


def test_a_lock_file_skips_only_the_pattern_naming_its_path(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.doctor_report import DoctorStatus
    from dadaia_workspace.infrastructure.privacy_check import check_public_privacy

    public = tmp_path / "lib" / "dadaia_workspace" / "public"
    public.mkdir(parents=True)
    write_text(public / "package-lock.json", f'{{"v": "{private_ip()}"}}\n')
    assert [line.status for line in check_public_privacy(public, lambda d: d.iterdir())] == [
        DoctorStatus.OK
    ]

    write_text(
        public / "package-lock.json", f'{{"v": "{private_ip()}", "h": "{internal_host("box")}"}}\n'
    )
    [hit] = check_public_privacy(public, lambda d: d.iterdir())
    assert "package-lock.json" in hit.text and "internal hostname" in hit.text

    (public / "package-lock.json").unlink()
    write_text(public / "notes.json", f'{{"v": "{private_ip()}"}}\n')
    [line] = check_public_privacy(public, lambda d: d.iterdir())
    assert line.status is DoctorStatus.ERROR and "notes.json" in line.text


def _workspace_with_terms(root: Path, terms: dict[str, str]) -> Path:
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    write_text(states / "spec_contexts.json", "{}")
    write_text(states / "privacy_denylist.json", json.dumps(terms))
    return root


def _repo_in(workspace: Path, name: str) -> Path:
    repo = workspace / "repos" / name
    repo.mkdir(parents=True)
    run(["git", "init", "-q", str(repo)])
    return repo


def test_the_denylist_of_a_scanned_path_is_its_own_workspaces_not_the_cwds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scanning a repo of workspace B from workspace A's cwd applies B's terms only."""
    monkeypatch.delenv("DADAIA_PRIVACY_DENYLIST", raising=False)
    cwd_ws = _workspace_with_terms(tmp_path / "wsa", {"zzcwdterm": "a"})
    repo = _repo_in(_workspace_with_terms(tmp_path / "wsb", {"zzplantedterm": "b"}), "app")
    monkeypatch.chdir(cwd_ws)

    assert load_privacy_terms(repo) == (("zzplantedterm", "b"),)
