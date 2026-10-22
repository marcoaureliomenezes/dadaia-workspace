#!/usr/bin/env python3
"""The closure worklist: which atoms the window's code changes touched, and which code no
atom describes at all.

A pure function of the atom files' `sources`, `git diff --name-only <since>..HEAD` and `git
ls-files`; `release.py memory` imports :func:`report`, so no caller hands it a worklist.

`sources` globs are matched with `fnmatch` over repo-relative POSIX paths, where `*` and
`**` both cross `/`: a prefix glob (`features/specs/**`) is the shape the
lint requires, and a wider match here can only ADD an atom to the worklist, never hide one.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

import _git
from _frontmatter import parse as parse_block
from _frontmatter import split
from _platform import git_line, mkdir_line, read_text
from _refusal import Refusal as Refusal
from _specs import script

CODE = "LEDGER-MEMORY-SCHEMA"
PRODUCT = "memory/product"
INDEX = "memory/product/index.md"
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def parse(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """``(frontmatter, body, error)`` for one atom's text.

    The block is read by the kernel grammar; the atom rules are flat keys, each a
    single-line scalar or a list of them (an empty key is ``[]``).
    """
    parts = split(text)
    if parts is None:
        return None, "", "no YAML frontmatter found"
    try:
        data = parse_block(parts[0])
    except ValueError as exc:
        return None, "", f"frontmatter {exc}"
    for key, value in data.items():
        items = [] if value is None else value if isinstance(value, list) else [value]
        if not all(not isinstance(item, dict | list) and "\n" not in str(item) for item in items):
            return (
                None,
                "",
                f"frontmatter key {key!r} is not a flat single-line value or a list of them",
            )
        data[key] = [] if value is None else value
    return data, parts[1], None


def atoms(specs: Path) -> list[Path]:
    """Every feature atom under `product/`, in the alphabetical order `rank` follows."""
    product = specs / PRODUCT
    if not product.is_dir():
        raise Refusal(
            f"no {PRODUCT}/ under {specs} — there is no catalog to generate",
            mkdir_line(product),
        )
    return sorted(path for path in product.rglob("*.md") if path.name != "index.md")


def _depends_on(body: str) -> list[str]:
    """The body's `[[wikilink]]` slugs, first-occurrence order, deduplicated."""
    return list(dict.fromkeys(WIKILINK_RE.findall(body)))


def feature(path: Path, specs: Path, rank: int) -> dict[str, Any]:
    """One catalog entry built from *path*'s frontmatter and body."""
    data, body, error = parse(read_text(path))
    if error is not None or data is None:
        fix = script(Path(__file__).parents[2] / "dd-spec-navigator" / "scripts" / "memory.py")(
            "check"
        )
        raise Refusal(f"{path}: {error}", fix)
    sources = [str(item) for item in data.get("sources") or []]
    return {
        "rank": rank,
        "slug": str(data.get("slug", path.stem)),
        "title": str(data.get("title", data.get("slug", path.stem))),
        "area": "product" if path.parent == specs / PRODUCT else path.parent.name,
        "tldr": str(data.get("tldr", "")),
        "summary": str(data.get("summary", "")),
        "path": path.relative_to(specs.parent).as_posix(),
        "tags": list(data.get("tags") or []),
        "token_estimate": round(len(body.split()) * 1.35),
        "depends_on": _depends_on(body),
        **({"sources": sources} if sources else {}),
    }


def entries(specs: Path) -> list[dict[str, Any]]:
    """The feature entries the atom files declare, in `atoms` order; none without a product tree."""
    if not (specs / PRODUCT).is_dir():
        return []
    return [feature(path, specs, rank) for rank, path in enumerate(atoms(specs), start=1)]


NOT_CODE = frozenset({"specs", "tests", "test", "docs"})


def _cut(repo: Path, what: str) -> Refusal | None:
    """The one refusal naming a history cut: *repo* is a shallow clone, else None."""
    if not _git.shallow(repo):
        return None
    return Refusal(
        f"{what}: a shallow clone lacks the window's history",
        git_line(repo, "fetch", "--unshallow"),
    )


def git(repo: Path, *argv: str) -> list[str]:
    """`git *argv` from *repo*, as non-empty lines; a git that refuses is a Refusal."""
    try:
        out = _git.git(repo, *argv)
    except RuntimeError as exc:  # a bound-less caller's history precondition: a cut is named first
        raise _cut(repo, f"git {' '.join(argv)} failed in {repo}") or Refusal(
            str(exc),
            git_line(repo, *argv),
        ) from exc
    return [line for line in out.split("\n") if line]


def _root(repo: Path) -> str:
    if cut := _cut(repo, "no recorded window bound is reachable"):
        raise cut
    return git(repo, "rev-list", "--max-parents=0", "HEAD")[-1]


def reach(repo: Path, bounds: list[str]) -> str:
    """The newest of *bounds* (newest first) HEAD reaches, else the root commit: only widens."""
    return next((b for b in bounds if _git.reaches(repo, b)), None) or _root(repo)


def report(specs: Path, since: str, until: str = "HEAD") -> dict[str, Any]:
    """The worklist for the window *since*..*until* — the ONE decider every verb calls."""
    repo = specs.parent
    for bound in (since, until):  # usable = an ancestor of HEAD
        if bound == "HEAD" or _git.reaches(repo, bound):
            continue
        if cut := _cut(repo, f"{bound} is out of reach"):  # a cut is checked first
            raise cut
        if not _git.git(
            repo, "rev-parse", "--verify", "--quiet", f"{bound}^{{commit}}", check=False
        ).strip():
            raise Refusal(f"{bound} is not in this clone", git_line(repo, "fetch", "origin", bound))
        raise Refusal(f"{bound} is not an ancestor of HEAD — a clone of this branch lacks it (a rebase rewrote it)",
                      script(Path(__file__).parents[2] / "dd-spec-navigator" / "scripts" / "memory.py")(
                          "drift", "--since", _root(repo), specs=specs))  # fmt: skip
    catalog = {"features": entries(specs)}
    changed = git(repo, "diff", "--name-only", f"{since}..{until}")
    return {"since": since, **worklist(catalog, changed, git(repo, "ls-files"))}


def _units(tracked: list[str]) -> dict[str, list[str]]:
    """Every directory directly holding a tracked file, any language, mapped to every file
    beneath it; a root-level file belongs to no unit.

    Derived from the audited repo alone: `specs/`, `tests/`, `docs/` and dot-dirs hold no
    unit, so a parent directory is covered as soon as any child is.
    """
    units = {
        path.rpartition("/")[0]
        for path in tracked
        if "/" in path
        and not (top := path.split("/", 1)[0]).startswith(".")
        and top not in NOT_CODE
    }
    return {u: [p for p in tracked if p == u or p.startswith(f"{u}/")] for u in units}


def _matches(sources: list[str], paths: list[str]) -> list[str]:
    return sorted({p for p in paths for glob in sources if fnmatch.fnmatch(p, glob)})


def worklist(catalog: dict[str, Any], changed: list[str], tracked: list[str]) -> dict[str, Any]:
    """The two lists: atoms whose sources matched a changed path, and uncovered units.

    An atom with no `sources` covers nothing — it matches no change and leaves every unit
    it might have described in the uncovered list, which is exactly the drift to report.
    """
    features = catalog.get("features", [])
    atoms = [
        {"slug": str(f["slug"]), "path": str(f["path"]), "matched": matched}
        for f in features
        if (matched := _matches([str(s) for s in f.get("sources") or []], changed))
    ]
    covered = {
        unit
        for unit, inside in _units(tracked).items()
        for f in features
        if _matches([str(s) for s in f.get("sources") or []], inside)
    }
    uncovered = sorted(set(_units(tracked)) - covered)
    return {"atoms": atoms, "uncovered": uncovered}


def render(report: dict[str, Any]) -> str:
    """The human rendering — one line per atom to reconcile, one per uncovered unit."""
    lines = [f"[drift] since {report['since']}"]
    lines += [f"  atom {a['slug']} <- {', '.join(a['matched'])}" for a in report["atoms"]]
    lines += [f"  uncovered {unit}" for unit in report["uncovered"]]
    if len(lines) == 1:
        lines.append("  nothing drifted: every atom is current and every unit is covered")
    return "\n".join(lines)
