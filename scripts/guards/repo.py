"""Repository checks: the workflows, the release canon, canonical memory, the ADR ledger and
the specs canon's git visibility (QUALITY P-30, P-32, P-33; ADRs 0025, 0176).

Each check reads tracked files of the tree it is given; ``CONTROL`` copies the library's own
tracked files, so a green control is the checkout's truth and every plant edits one line.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from run import tracked  # noqa: E402

from dadaia_workspace.core.fixed_sections import extract_fixed_section  # noqa: E402
from dadaia_workspace.core.gitflow import read_gitflow  # noqa: E402
from dadaia_workspace.core.workspace_layout import render_registry_tables  # noqa: E402
from dadaia_workspace.features.specs.canon import CANON, TEMPLATES  # noqa: E402
from dadaia_workspace.infrastructure.ledger_scripts import load_owner  # noqa: E402

if TYPE_CHECKING:
    from run import Check, Plant, Tree

_WF = ".github/workflows"
_RELEASE = f"{_WF}/release.yml"
_ACTION = "googleapis/release-please-action"
_GATE = "needs.release-please.outputs.release_created == 'true'"
_MODEL_SECRET = re.compile(r"CLAUDE_API_KEY|ANTHROPIC_(?:API_)?KEY|api\.anthropic\.com", re.I)
_SKILLS_REPO = re.compile(
    r"dadaia-skills|SKILLS_REPO_TOKEN|build-skills-repo|npx skills add|skills-repository"
)
# Both dated release headings: hand-written `## [x.y.z] — date`, release-please's `(date)`.
_CHANGELOG_TOP = re.compile(
    r"^## \[(\d+\.\d+\.\d+)\](?:\([^)]*\))? (?:[-—] \d{4}-\d{2}-\d{2}|\(\d{4}-\d{2}-\d{2}\))\s*$",
    re.M,
)


def _yaml(tree: Tree, rel: str) -> dict[Any, Any]:
    return yaml.safe_load(tree.read(rel)) or {}


def _on(doc: dict[Any, Any]) -> Any:
    """PyYAML (YAML 1.1) reads the bare ``on:`` key as the boolean True."""
    return doc.get("on", doc.get(True)) or {}


def _workflows(tree: Tree) -> dict[str, dict[Any, Any]]:
    return {p: _yaml(tree, p) for p in tree.tracked(_WF) if p.endswith((".yml", ".yaml"))}


def _jobs(doc: dict[Any, Any]) -> dict[str, dict[str, Any]]:
    return {k: j for k, j in (doc.get("jobs") or {}).items() if isinstance(j, dict)}


def _needs(job: dict[str, Any]) -> list[str]:
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def _steps(tree: Tree) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (p, jid, s)
        for p, doc in _workflows(tree).items()
        for jid, job in _jobs(doc).items()
        for s in job.get("steps") or []
    ]


def _records(tree: Tree) -> list[dict[str, Any]]:
    path = tree.root / "specs" / "ADRs" / "decisions.jsonl"
    return list(load_owner("dd-bug-resolution", "_ledger").records(path))


def no_model_calls_in_ci(tree: Tree) -> list[str]:
    """P-33 (ADR 0025): no ``anthropics/*`` action, model secret or endpoint in a workflow."""
    out = []
    for p, doc in _workflows(tree).items():
        jobs = _jobs(doc).values()
        uses = [str(j.get("uses", "")) for j in jobs]
        uses += [str(s.get("uses", "")) for j in jobs for s in j.get("steps") or []]
        out += [
            f"anthropic-action: {p} uses {u}" for u in uses if u.lower().startswith("anthropics/")
        ]
        lines = enumerate(tree.read(p).splitlines(), 1)
        out += [f"model-secret: {p}:{n}" for n, line in lines if _MODEL_SECRET.search(line)]
    return out


def workflow_never_rules(tree: Tree) -> list[str]:
    wfs, steps = _workflows(tree), _steps(tree)
    text = {p: tree.read(p) for p in wfs}
    release = _jobs(wfs.get(_RELEASE, {}))
    surfaces = [*wfs, *tree.tracked("README.md", "llms.txt", "docs/*.md", "specs/memory/*.md")]
    cov = [
        f"{p}:{jid}"
        for p, doc in wfs.items()
        for jid, job in _jobs(doc).items()
        for s in job.get("steps") or []
        if "pytest" in (run := s.get("run") or "")
        and "--cov" in run
        and "runner.temp"
        not in str(
            (s.get("env") or {}).get("COVERAGE_FILE") or (job.get("env") or {}).get("COVERAGE_FILE")
        )
    ]
    never = {
        # Grill Q14: no standalone skills repository was ordered.
        "skills-repository-published": [
            f"{p}:{n}"
            for p in surfaces
            for n, line in enumerate(tree.read(p).splitlines(), 1)
            if _SKILLS_REPO.search(line)
        ],
        # the template-injection shape: every value reaches a run body through env:
        "workflow-expression-in-a-run-body": [
            f"{p}/{j}: {line.strip()}"
            for p, j, s in steps
            for line in (s.get("run") or "").splitlines()
            if "${{" in line
        ],
        "coverage-file-in-the-checkout": cov,
        "release-please-outside-release-yml": [
            p for p in wfs if _ACTION in text[p] and p != _RELEASE
        ],
        "pypi-publisher-outside-release-yml": [
            p for p in wfs if "pypa/gh-action-pypi-publish" in text[p] and p != _RELEASE
        ],
        # same-workflow chaining only: a second trigger would need a PAT (PLAN D8)
        "release-event-or-tag-push-trigger": [
            p
            for p, doc in wfs.items()
            if "release" in (t := _on(doc))
            or (isinstance(t, dict) and bool({"tags", "tags-ignore"} & set(t.get("push") or {})))
        ],
        "publishing-job-without-the-release-gate": [
            j
            for j, job in release.items()
            if j != "release-please"
            and ("release-please" not in _needs(job) or str(job.get("if") or "").strip() != _GATE)
        ],
        "needs-an-undefined-job": [
            f"{j} -> {d}" for j, job in release.items() for d in _needs(job) if d not in release
        ],
        # T-047-88: the action mints the tag, never workflow arithmetic
        "hand-computed-tag": [
            f"{j}: {line.strip()}"
            for p, j, s in steps
            if p == _RELEASE
            for line in (s.get("run") or "").splitlines()
            if "git ls-remote --tags" in line or "git tag " in line
        ],
    }
    return [f"{rule}: {hits}" for rule, hits in never.items() if hits]


def release_workflow_canon(tree: Tree) -> list[str]:
    """P-30: the main-only pinned release-please, the one gated publish chain, the manifest
    floor and patch rule, and the pyproject version equal to the CHANGELOG's top section."""
    doc = _yaml(tree, _RELEASE)
    on, jobs = _on(doc), _jobs(doc)
    rp, build = jobs.get("release-please", {}), jobs.get("build", {})
    pins = [ln for ln in tree.read(_RELEASE).splitlines() if _ACTION in ln and "uses:" in ln]
    ref, _, comment = (pins[0] if len(pins) == 1 else "@").partition("#")
    step: dict[str, Any] = next(
        (s for s in rp.get("steps") or [] if _ACTION in str(s.get("uses"))), {}
    )
    inputs = step.get("with") or {}
    version: dict[str, Any] = next(
        (s for s in build.get("steps") or [] if s.get("id") == "version"), {}
    )
    existing: dict[str, Any] = next(
        (s for s in rp.get("steps") or [] if s.get("id") == "existing"), {}
    )
    manifest = json.loads(tree.read(".release-please-manifest.json"))
    config = json.loads(tree.read("release-please-config.json"))
    sections = {e["type"]: e for e in config.get("changelog-sections") or []}
    minted = tomllib.loads(tree.read("pyproject.toml"))["tool"]["poetry"]["version"]
    top = _CHANGELOG_TOP.search(tree.read("CHANGELOG.md"))
    tags = subprocess.run(
        ["git", "tag", "-l", "v*", "--sort=version:refname"],
        cwd=tree.root, capture_output=True, text=True, check=False,
    ).stdout.split()  # fmt: skip
    clauses = {
        "main-only": (on.get("push") or {}).get("branches") == ["main"]
        and "workflow_dispatch" in on
        and str(rp.get("if") or "").strip() == "github.ref == 'refs/heads/main'",
        "write-scope": doc.get("permissions") == {"contents": "write", "pull-requests": "write"},
        "sha-pinned": bool(re.fullmatch(r"[0-9a-f]{40}", ref.split("@", 1)[1].strip()))
        and bool(re.fullmatch(r"\s*v\d+\.\d+\.\d+\s*", comment)),
        "config-driven": step.get("id") == "release-please"
        and "release-type" not in inputs
        and inputs.get("config-file") == "release-please-config.json"
        and inputs.get("manifest-file") == ".release-please-manifest.json",
        "publish-chain": jobs.get("publish", {}).get("environment") == "pypi"
        and (jobs.get("publish", {}).get("permissions") or {}).get("id-token") == "write"
        and jobs.get("approve", {}).get("environment") == "release-gate"
        and (build.get("outputs") or {}).get("version") == "${{ steps.version.outputs.version }}"
        and version.get("env") == {"TAG": "${{ needs.release-please.outputs.tag_name }}"}
        and 'echo "version=${TAG#v}" >> "$GITHUB_OUTPUT"' in str(version.get("run"))
        and {j for j, job in jobs.items() if "needs.build.outputs.version" in yaml.safe_dump(job)}
        == {"approve", "publish", "smoke-test"},
        "republish-tag": "tag" in ((on.get("workflow_dispatch") or {}).get("inputs") or {})
        and "inputs.tag" in str(existing.get("if"))
        and ((build.get("steps") or [{}])[0].get("with") or {}).get("ref")
        == "${{ needs.release-please.outputs.tag_name }}",
        # sa-doctor-job-not-a-required-check#B2: the build waits for ci.yml itself
        "ci-gated-build": jobs.get("ci", {}).get("uses") == "./.github/workflows/ci.yml"
        and "ci" in _needs(build)
        and not any("pytest" in yaml.safe_dump(job) for job in jobs.values()),
        "manifest-floor": set(manifest) == {"."} and minted == manifest["."],
        # the floor is the last published tag (a shallow clone has none)
        "published-floor": not tags or tags[-1] == f"v{manifest['.']}",
        "patch-below-one": config.get("bump-minor-pre-major") is True
        and config.get("bump-patch-for-minor-pre-major") is True
        and config.get("include-component-in-tag") is False
        and config["packages"]["."].get("release-type") == "python"
        and config["packages"]["."].get("changelog-path") == "CHANGELOG.md"
        and {"feat", "fix", "refactor", "docs", "ci", "test", "chore"} <= set(sections)
        and all(e.get("section") and isinstance(e.get("hidden"), bool) for e in sections.values()),
        "version-equals-changelog": top is not None and top.group(1) == minted,
    }
    return [
        f"{c}: release.yml / release-please / version clause broken"
        for c, ok in clauses.items()
        if not ok
    ]


_SECTIONS = {
    "ARCHITECTURE.md": (["Principles", "Tech Stack", "Structure"], "slop-code"),
    "QUALITY.md": (["Principles", "Test architecture", "Gates"], "slop-tests"),
}
_TOP = re.compile(r"^## (.+?)\s*$", re.M)
_HISTORY = re.compile(r"^#{1,6}\s*(Changelog|History|Hist[oó]rico|Versions)\b", re.M | re.I)
_PRINCIPLE = re.compile(r"^### P-(\d{2}) ·.*$", re.M)
_BLOCK_END = re.compile(r"^(?:### P-\d{2} ·|## )", re.M)
_MEASURED = re.compile(r"^Measured by: .+$", re.M)
_ADR_LINE = re.compile(r"^ADR: (?:none|(\d{4}) \((?:proposed|accepted)\b.*\))\s*$", re.M)


def memory_canonical_shape(tree: Tree) -> list[str]:
    """P-32 (0.4.7 FR1, ADR 0023): its nine rules over the canonical pair."""
    top = sorted(
        Path(p).name
        for p in tree.tracked("specs/memory")
        if p.count("/") == 2 and p.endswith(".md")
    )
    out = []
    if top != ["AGENTS.md", *_SECTIONS]:
        out.append(f"canonical-pair: specs/memory holds {top}")
    known, seen = {r["id"] for r in _records(tree)}, set()
    for name, (sections, fixed) in _SECTIONS.items():
        text = tree.read(f"specs/memory/{name}")
        if (heads := _TOP.findall(text)) != sections:
            out.append(f"section-order: {name} has {heads}")
        if not extract_fixed_section(text, fixed):
            out.append(f"fixed-block: {name} lost `{fixed}`")
        if m := _HISTORY.search(text):
            out.append(f"history-heading: {name} carries {m.group(0)!r}")
        start = text.find("## Principles")
        end = (
            (m.start() if (m := _TOP.search(text, start + 1)) else len(text)) if start >= 0 else -1
        )
        foreign = set(re.findall(r"\[\[([^\]]+)\]\]", text)) - {"ARCHITECTURE", "QUALITY"}
        if foreign:
            out.append(f"atom-link: {name} links {sorted(foreign)}")
        for h in _PRINCIPLE.finditer(text):
            pid, nxt = h.group(1), _BLOCK_END.search(text, h.end())
            body = text[h.end() : nxt.start() if nxt else len(text)]
            if not start < h.start() < end:
                out.append(f"principle-placement: {name} P-{pid} sits outside ## Principles")
            if pid in seen:
                out.append(f"unique-ids: P-{pid} appears twice across the pair")
            seen.add(pid)
            adr = _ADR_LINE.search(body)
            if not _MEASURED.search(body) or not adr:
                out.append(f"principle-lines: {name} P-{pid} lacks `Measured by:` or `ADR:`")
            elif adr.group(1) and adr.group(1) not in known:
                out.append(f"adr-exists: {name} P-{pid} cites missing ADR {adr.group(1)}")
    return out


def adr_superseded_successor(tree: Tree) -> list[str]:
    records = _records(tree)
    named = {i for r in records for i in (r.get("supersedes") or "").split(",") if i}
    orphans = sorted(
        r["id"] for r in records if r["status"] == "superseded" and r["id"] not in named
    )
    return [f"orphan-superseded: {orphans} named by no successor's supersedes"] if orphans else []


def ci_triggers_gitflow(tree: Tree) -> list[str]:
    """T-050-19 AC6.9: the literal triggers are the library constitution's gitflow."""
    flow, warning = read_gitflow(tree.root / "specs")
    ci, release = _on(_yaml(tree, f"{_WF}/ci.yml")), _on(_yaml(tree, _RELEASE))
    scan = _yaml(tree, f"{_WF}/secret-scan.yml")
    edges = [flow.principal, flow.integration]
    bot = _yaml(tree, ".github/dependabot.yml").get("updates") or []
    clauses = {
        "gitflow-unread": warning is None,
        "ci-triggers": ci["push"]["branches"] == [*edges, f"{flow.work_prefix}**"]
        and ci["pull_request"]["branches"] == edges,
        "release-trigger": release["push"]["branches"] == [flow.principal],
        # A-12.1/A-12.2: the required gitleaks context reports on both PR edges
        "secret-scan-edges": _on(scan)["pull_request"]["branches"] == edges
        and _on(scan)["push"]["branches"] == [flow.principal]
        and _jobs(scan).get("gitleaks", {}).get("name") == "gitleaks",
        "no-hotfix": "hotfix" not in tree.read(f"{_WF}/secret-scan.yml"),
        "dependabot-target": bool(bot)
        and {u.get("target-branch") for u in bot} == {flow.integration},
    }
    return [
        f"{c}: the triggers drift from the gitflow block" for c, ok in clauses.items() if not ok
    ]


_RENAMED = "---\nspecs_pattern_version: 6\ngitflow: {principal: trunk, integration: next, work: work/}\n---\n# C\n"
# ADR 0021: main takes develop and release-please's own branch; develop takes feature/ and
# Dependabot; T-050-19 AC6.8: a renamed gitflow moves the rules; no constitution, the default.
_SOURCES = [
    ("repo", "develop", "main", True),
    ("repo", "release-please--branches--main", "main", True),
    ("repo", "feature/0.4.7", "main", False),
    ("repo", "release-please--branches--develop", "main", False),
    ("repo", "feature/0.4.7", "develop", True),
    ("repo", "develop", "develop", False),
    ("repo", "dependabot/pip/ruff-0.16.8", "develop", True),
    ("repo", "dependabot/github_actions/actions/checkout-7.1.0", "develop", True),
    ("repo", "dependabot/pip/ruff-0.16.8", "main", False),
    ("renamed", "next", "trunk", True),
    ("renamed", "develop", "trunk", False),
    ("renamed", "work/1.2.3", "next", True),
    ("renamed", "feature/1.2.3", "next", False),
    ("absent", "develop", "main", True),
    ("absent", "feature/0.5.0", "main", False),
]


def pr_source_guard_release_pr(tree: Tree) -> list[str]:
    """pr-source-guard's step exactly as CI runs it, against each base gitflow."""
    job = _jobs(_yaml(tree, f"{_WF}/ci.yml")).get("pr-source-guard", {})
    run = next((s["run"] for s in job.get("steps") or [] if "HEAD_REF" in (s.get("env") or {})), "")
    out = []
    with tempfile.TemporaryDirectory(prefix="guard-gitflow-") as tmp:
        specs = {"repo": tree.root / "specs", "renamed": Path(tmp, "r"), "absent": Path(tmp, "a")}
        specs["renamed"].mkdir()
        (specs["renamed"] / "constitution.md").write_text(_RENAMED, encoding="utf-8")
        for gitflow, head, base, allowed in _SOURCES:
            env = {**os.environ, "HEAD_REF": head, "BASE_REF": base,
                   "PYTHONPATH": str(ROOT), "BASE_SPECS": str(specs[gitflow]),
                   "PATH": os.pathsep.join([str(Path(sys.executable).parent), os.environ["PATH"]])}  # fmt: skip
            ok = subprocess.run(["bash", "-c", run or "exit 1"], env=env, cwd=tree.root,
                                capture_output=True).returncode == 0  # fmt: skip
            if ok != allowed:
                out.append(f"{'admits' if ok else 'refuses'}: {gitflow} {base} <- {head}")
    return out


def ci_checkout_history(tree: Tree) -> list[str]:
    """ci-history-depth-is-decided-per-job: every ci.yml checkout fetches depth 0."""
    depths = [
        (jid, (s.get("with") or {}).get("fetch-depth"))
        for jid, job in _jobs(_yaml(tree, f"{_WF}/ci.yml")).items()
        for s in job.get("steps") or []
        if str(s.get("uses", "")).startswith("actions/checkout@")
    ]
    shallow = [jid for jid, d in depths if d != 0] if depths else ["(no checkout)"]
    return [f"shallow-checkout: {shallow}"] if shallow else []


def required_checks_listed(tree: Tree) -> list[str]:
    """sa-doctor-job-not-a-required-check#B1: an unlisted PR check is red-but-mergeable;
    a stale entry blocks every merge."""
    contexts: set[str] = set()
    for doc in _workflows(tree).values():
        if "pull_request" in _on(doc):
            for jid, job in _jobs(doc).items():
                name = job.get("name", jid)
                matrix = ((job.get("strategy") or {}).get("matrix") or {}).get("os")
                contexts |= {f"{name} ({v})" for v in matrix} if matrix else {name}
    required = set(json.loads(tree.read(".github/required-checks.json")))
    out = [f"unlisted-check: {sorted(contexts - required)}"] if contexts - required else []
    return out + ([f"stale-entry: {sorted(required - contexts)}"] if required - contexts else [])


def onboarding_journey_uv(tree: Tree) -> list[str]:
    """0.4.8 AC8.3: the e2e job installs uv, requires uvx and runs the journey; the
    post-publish smoke walks init --repo, specs init and doctor."""

    def texts(wf: str, job: str) -> str:
        steps = _jobs(_yaml(tree, f"{_WF}/{wf}")).get(job, {}).get("steps") or []
        return "\n".join(f"{s.get('run', '')}\n{s.get('env', '')}" for s in steps)

    e2e, smoke = texts("ci.yml", "e2e-python"), texts("release.yml", "smoke-test")
    needles = (
        'uvx "dadaia-workspace==$VERSION" init',
        "--repo",
        "specs init --context",
        "doctor --context",
    )
    out = []
    if not ("install uv==" in e2e and "'DADAIA_REQUIRE_UVX': '1'" in e2e
            and re.search(r"tests/e2e(?:\s|$|/test_onboarding_journey\.py)", e2e)):  # fmt: skip
        out.append("e2e-uv: the e2e job does not require uvx over the journey")
    return out + [f"smoke-greenfield: smoke-test lacks {n!r}" for n in needles if n not in smoke]


def specs_canon_tracked(tree: Tree) -> list[str]:
    """AC8.3: one probe per CANON row, judged by the tree's .gitignore. A row is meant to be
    ignored only when its template renders registry tables (a projection), plus the two
    archived scratch shapes."""
    expect: dict[str, bool] = {}
    for row in CANON:
        kind, src = TEMPLATES.get(row.shape, ("static", ""))
        text = (
            (ROOT / "dadaia_workspace/public" / src).read_text("utf-8") if kind == "copy" else src
        )
        expect["specs/" + re.sub(r"<[^>]+>|\*\*", "1", row.shape)] = (
            render_registry_tables(text) != text
        )
    expect |= {
        "specs/releases/_archive/1/local-notes.md": True,
        "specs/releases/_archive/1/tmp/x": True,
    }
    ignored = set(subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"], cwd=tree.root,
        input="\n".join(expect), capture_output=True, text=True, check=False,
    ).stdout.split())  # fmt: skip
    return [
        f"canon-ignored: {p} is canon yet ignored"
        for p, e in expect.items()
        if not e and p in ignored
    ] + [
        f"ignore-lost: {p} should stay ignored" for p, e in expect.items() if e and p not in ignored
    ]


# --- plants: CONTROL is the library's own files; each plant edits one line of it ---------

_COPIED = (".github", ".gitignore", "specs/constitution.md", "specs/memory", "specs/ADRs",
           "pyproject.toml", "CHANGELOG.md", ".release-please-manifest.json",
           "release-please-config.json", "README.md", "llms.txt", "docs")  # fmt: skip
_ROGUE = (
    "on: push\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: anthropics/a@v1\n"
)


def CONTROL(root: Path) -> None:
    """Every check green on a copy of the tracked library files; an untracked, excluded
    workflow breaking the CI rules stays out (bugs 465, 467: untracked is never read)."""
    for rel in tracked(ROOT, *_COPIED):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, root / rel)
    (root / ".git/info/exclude").write_text(f"{_WF}/zz.yml\n", encoding="utf-8")
    (root / _WF / "zz.yml").write_text(
        _ROGUE + "        run: echo ${{ secrets.ANTHROPIC_KEY }}\n", "utf-8"
    )


def _edit(rel: str, old: str, new: str) -> Plant:
    """CONTROL with *old*'s first occurrence in *rel* replaced (appended when *old* is empty)."""

    def plant(root: Path) -> None:
        CONTROL(root)
        path = root / rel
        text = path.read_text("utf-8") if path.exists() else ""
        if old and old not in text:
            raise AssertionError(f"plant anchor lost in {rel}: {old!r}")
        path.write_text(text.replace(old, new, 1) if old else text + new, encoding="utf-8")

    return plant


def _workflow(steps: str, on: str = "push") -> Plant:
    head = f"on: {on}\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n"
    return _edit(f"{_WF}/planted.yml", "", head + steps)


def _tag(root: Path) -> None:
    CONTROL(root)
    git = ["git", "-c", "user.name=g", "-c", "user.email=g@example.invalid"]
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "g"], cwd=root, check=True)
    subprocess.run(["git", "tag", "v99.0.0"], cwd=root, check=True)


def _unlink(rel: str) -> Plant:
    def plant(root: Path) -> None:
        CONTROL(root)
        (root / rel).unlink()

    return plant


_A, _Q, _G = "specs/memory/ARCHITECTURE.md", "specs/memory/QUALITY.md", f"{_WF}/ci.yml"
_GATED_JOB = f"  rogue:\n    needs: [release-please, ghost]\n    if: {_GATE}\n    runs-on: x\n"
_SUPERSEDED = json.dumps({"id": "9999", "status": "superseded", "supersedes": None}) + "\n"

CHECKS: dict[str, Check] = {
    "no-model-api-in-ci": (
        no_model_calls_in_ci,
        {
            "anthropic-action": _workflow("      - uses: anthropics/claude-code-action@v1\n"),
            "model-secret": _workflow(
                "      - env: {K: x}\n        run: echo $ANTHROPIC_API_KEY\n"
            ),
        },
    ),
    "workflow-never-rules": (
        workflow_never_rules,
        {
            "skills-repository-published": _edit("README.md", "", "\nnpx skills add dadaia\n"),
            "workflow-expression-in-a-run-body": _workflow(
                "      - run: echo ${{ github.head_ref }}\n"
            ),
            "coverage-file-in-the-checkout": _workflow("      - run: pytest --cov x\n"),
            "release-please-outside-release-yml": _workflow(f"      - uses: {_ACTION}@v5\n"),
            "pypi-publisher-outside-release-yml": _workflow(
                "      - uses: pypa/gh-action-pypi-publish@v1\n"
            ),
            "release-event-or-tag-push-trigger": _workflow(
                "      - run: echo\n", "{push: {tags: [v*]}}"
            ),
            "publishing-job-without-the-release-gate": _edit(
                _RELEASE,
                "    needs: [release-please, build, approve]\n",
                "    needs: [build, approve]\n",
            ),
            "needs-an-undefined-job": _edit(_RELEASE, "", _GATED_JOB),
            "hand-computed-tag": _edit(
                _RELEASE,
                "      - run: pipx install",
                "      - run: git tag v9\n      - run: pipx install",
            ),
        },
    ),
    "release-workflow-canon": (
        release_workflow_canon,
        {
            "main-only": _edit(_RELEASE, "    if: github.ref == 'refs/heads/main'\n", ""),
            "write-scope": _edit(
                _RELEASE, "  contents: write\n", "  contents: write\n  packages: write\n"
            ),
            "sha-pinned": _edit(_RELEASE, f"{_ACTION}@", f"{_ACTION}@v5.0.0 "),
            "config-driven": _edit(
                _RELEASE,
                "          config-file:",
                "          release-type: python\n          config-file:",
            ),
            "publish-chain": _edit(
                _RELEASE, "    environment: pypi\n", "    environment: release-gate\n"
            ),
            "republish-tag": _edit(_RELEASE, "inputs.tag != ''", "true"),
            "ci-gated-build": _edit(
                _RELEASE, "    needs: [release-please, ci]\n", "    needs: [release-please]\n"
            ),
            "manifest-floor": _edit(".release-please-manifest.json", '": "', '": "9'),
            "published-floor": _tag,
            "patch-below-one": _edit(
                "release-please-config.json",
                '"bump-patch-for-minor-pre-major": true',
                '"bump-patch-for-minor-pre-major": false',
            ),
            "version-equals-changelog": _edit(
                "CHANGELOG.md", "\n## [", "\n## [9.9.9] — 2026-01-01\n\n## ["
            ),
        },
    ),
    "memory-canonical-shape": (
        memory_canonical_shape,
        {
            "canonical-pair": _edit("specs/memory/TECHSTACK.md", "", "# retired\n"),
            "section-order": _edit(_A, "\n## Structure", "\n## Notes\n\n## Structure"),
            "fixed-block": _edit(_Q, "slop-tests", "slop-gone"),
            "history-heading": _edit(_A, "\n## Tech Stack", "\n### Changelog\n\n## Tech Stack"),
            "principle-lines": _edit(_A, "\nMeasured by: ", "\nMeasured: "),
            "unique-ids": _edit(_Q, "### P-2", "### P-0"),
            "adr-exists": _edit(_A, "ADR: 0001 (accepted)", "ADR: 9999 (accepted)"),
            "principle-placement": _edit(_A, "\n## Structure", "\n### P-99 · x\n\n## Structure"),
            "atom-link": _edit(_Q, "\n## Gates", "\nSee [[sdd-gate-v3]].\n\n## Gates"),
        },
    ),
    "adr-superseded-successor": (
        adr_superseded_successor,
        {"orphan-superseded": _edit("specs/ADRs/decisions.jsonl", "", _SUPERSEDED)},
    ),
    "ci-triggers-gitflow": (
        ci_triggers_gitflow,
        {
            "gitflow-unread": _unlink("specs/constitution.md"),
            "ci-triggers": _edit(_G, "branches: [main, develop]", "branches: [main]"),
            "release-trigger": _edit(_RELEASE, "branches: [main]", "branches: [main, develop]"),
            "secret-scan-edges": _edit(f"{_WF}/secret-scan.yml", "[main, develop]", "[main]"),
            "no-hotfix": _edit(
                f"{_WF}/secret-scan.yml", "      - main\n", "      - main\n      - hotfix\n"
            ),
            "dependabot-target": _edit(
                ".github/dependabot.yml", "target-branch: develop", "target-branch: main"
            ),
        },
    ),
    "pr-source-guard-release-pr": (
        pr_source_guard_release_pr,
        {
            # pr-source-guard-refuses-the-release-please-pr-to-main, planted back
            "refuses": _edit(_G, ', f"release-please--branches--{flow.principal}"', ""),
            "admits": _edit(_G, 'ok = flow.role_of(head) == "work" or', "ok = True or"),
        },
    ),
    "ci-checkout-history": (
        ci_checkout_history,
        {"shallow-checkout": _edit(_G, "fetch-depth: 0", "fetch-depth: 1")},
    ),
    "required-checks-listed": (
        required_checks_listed,
        {
            "unlisted-check": _edit(
                _G, "    name: Guards (scripts/guards)", "    name: Guards renamed"
            ),
            "stale-entry": _edit(".github/required-checks.json", "[", '["Retired job",'),
        },
    ),
    "onboarding-journey-uv": (
        onboarding_journey_uv,
        {
            "e2e-uv": _edit(_G, 'DADAIA_REQUIRE_UVX: "1"', 'DADAIA_REQUIRE_UVX: "0"'),
            "smoke-greenfield": _edit(_RELEASE, "specs init --context", "specs init"),
        },
    ),
    "specs-canon-tracked": (
        specs_canon_tracked,
        {
            "canon-ignored": _edit(".gitignore", "", "/specs/releases/**/TASKS.md\n"),
            "ignore-lost": _edit(".gitignore", "", "!/specs/releases/_archive/**/local-notes.md\n"),
        },
    ),
}
