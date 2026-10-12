"""Diff-scoped mutation: ``python scripts/mutate.py --base <ref>`` mutates the lines
``git diff -U0 <ref>`` adds to non-test ``.py`` files, at most ``CAP`` mutants per line, and
prints ``SURVIVED|KILLED|TIMEOUT|UNCOVERED <file>:<line> <kind>: <old> -> <new> [killing
tests]``, the mutation score and the diff's line and branch coverage from one baseline run.
``--module <path>...`` mutates every line of those files instead (no diff, no coverage
lines). Tests per file come from running ``impact.py`` unless ``--tests <path>...`` names
them. A mutant run longer than ``--timeout`` seconds counts as killed and names no killer.
Before mutating a file its tests run once under coverage: a mutant runs every selected test,
except that a line no selected test executed, when none of them started a child through
``subprocess``, prints ``UNCOVERED`` and runs nothing (counted in the score's total, not
killed). A mutant run uses ``--continue-on-collection-errors``, and a test file that fails
to import credits every collected test of that file. The mutant timeout
is the larger of ``--timeout`` and three times that baseline run's wall time. A
baseline that fails prints ``BASELINE RED <file>: <failed ids>`` and exits 1 before any
mutation. ``--home <id>`` (a file, a node id or a prefix) adds, after the score,
``DELETABLE`` for each other test whose every killed mutant the home also kills, ``KEPT``
for the rest and ``NO-KILL`` for a test that ran and killed none. Refuses a dirty tracked
tree; every mutated file is restored byte for byte. Standard library plus ``pytest-cov``;
exit 0 on success, 1 on a red baseline, 2 on a usage error."""

from __future__ import annotations

import argparse
import ast
import inspect
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tokenize
from pathlib import Path

from coverage import CoverageData

ROOT = Path(__file__).resolve().parents[1]
CAP = 3
_COMPARE = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "=="}
_ARITH = {"+": "-", "-": "+", "*": "+"}
_BOOL = {"and": "or", "or": "and"}
_KINDS = ("compare", "bool", "not", "arith", "return", "const")
# kind, line, start (row, col), end (row, col), old text, new text
Mutant = tuple[str, int, tuple[int, int], tuple[int, int], str, str]


def _run(
    *args: str, env: dict[str, str] | None = None, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )


def changed_lines(diff: str) -> dict[str, set[int]]:
    """Added line numbers per ``.py`` file outside ``tests/`` in a ``-U0`` diff."""
    found: dict[str, set[int]] = {}
    path = ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
            if not path.endswith(".py") or path.startswith("tests/"):
                path = ""
        elif path and (hunk := re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", line)):
            start, count = int(hunk[1]), int(hunk[2] or 1)
            found.setdefault(path, set()).update(range(start, start + count))
    return found


def _mutants(text: str, lines: set[int]) -> list[Mutant]:
    rows = text.splitlines(keepends=True)
    found: list[Mutant] = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        row, col = tok.start
        if row not in lines:
            continue
        end = tok.end
        new, kind = "", ""
        if tok.type == tokenize.OP and tok.string in _COMPARE:
            kind, new = "compare", _COMPARE[tok.string]
        elif tok.type == tokenize.OP and tok.string in _ARITH:
            kind, new = "arith", _ARITH[tok.string]
        elif tok.type == tokenize.NAME and tok.string in _BOOL:
            kind, new = "bool", _BOOL[tok.string]
        elif tok.type == tokenize.NAME and tok.string == "not":
            kind, new = "not", ""
            end = (row, col + 4 if tok.line[col + 3 : col + 4] == " " else col + 3)
        elif tok.type == tokenize.NAME and tok.string in ("True", "False"):
            kind, new = "const", str(tok.string == "False")
        elif tok.type == tokenize.NUMBER and tok.string.isdecimal():
            kind, new = "const", str(int(tok.string) + 1)
        if kind:
            found.append((kind, row, (row, col), end, tok.string, new))
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Return) and node.value and node.lineno in lines:
            span = (node.value.lineno, node.value.end_lineno or 0)
            start = (span[0], len(rows[span[0] - 1].encode()[: node.value.col_offset].decode()))
            stop = (span[1], len(rows[span[1] - 1].encode()[: node.value.end_col_offset].decode()))
            old = ast.get_source_segment(text, node.value) or ""
            found.append(("return", node.lineno, start, stop, " ".join(old.split()), "None"))
    found.sort(key=lambda m: (m[1], _KINDS.index(m[0]), m[2]))
    per_line: dict[int, int] = {}
    kept = []
    for m in found:
        per_line[m[1]] = per_line.get(m[1], 0) + 1
        if per_line[m[1]] <= CAP:
            kept.append(m)
    return kept


def _apply(text: str, m: Mutant) -> str:
    rows = text.splitlines(keepends=True)
    offset = [sum(map(len, rows[: r - 1])) for r in (m[2][0], m[3][0])]
    return text[: offset[0] + m[2][1]] + m[5] + text[offset[1] + m[3][1] :]


def _tests_for(path: str) -> list[str]:
    done = _run(sys.executable, "scripts/impact.py", path)
    return [line[6:] for line in done.stdout.splitlines() if line.startswith("test: ")]


def _test_ids(tests: list[str], env: dict[str, str]) -> set[str]:
    done = _run(
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov",
        "--collect-only", *tests, env=env,
    )  # fmt: skip
    return {x for x in done.stdout.splitlines() if re.fullmatch(r"[\w./-]+\.py::\S+", x)}


def _killers(
    tests: list[str], ran: set[str], env: dict[str, str], timeout: float
) -> list[str] | None:
    done = _run(
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov", "--tb=no",
        "-rfE", "--continue-on-collection-errors", *tests, env=env, timeout=timeout,
    )  # fmt: skip
    if done.returncode == 0:
        return None
    found = set(re.findall(r"^(?:FAILED|ERROR) (\S+)", done.stdout, re.M))
    return sorted({t for t in found if "::" in t} | {t for t in ran if t.split("::")[0] in found})


def _executed(name: str, tests: list[str], env: dict[str, str]) -> tuple[set[int], bool, float]:
    """The lines of ``name`` some test executed, whether a test started a ``subprocess``
    child, and the baseline's wall seconds. A red baseline prints ``BASELINE RED`` and exits 1."""
    with tempfile.TemporaryDirectory(prefix="dadaia-mutate-") as tmp:
        data = str(Path(tmp, ".coverage"))
        began = time.monotonic()
        done = _run(
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "scripts.covdata",
            f"--cov={name.split('/')[0]}", "--cov=subprocess", "--cov-report=", "--tb=no",
            "-rfE", *tests, env={**env, "COVERAGE_FILE": data},
        )  # fmt: skip
        wall = time.monotonic() - began
        if done.returncode:
            failed = sorted(set(re.findall(r"^(?:FAILED|ERROR) (\S+)", done.stdout, re.M)))
            print(f"BASELINE RED {name}: {', '.join(failed)}")
            sys.exit(1)
        cov = CoverageData(basename=data)
        cov.read()
        # ponytail: children started by os.system, os.exec*, a direct os.posix_spawn or
        # multiprocessing are not detected; extend the spawner lines to cover them.
        src, first = inspect.getsourcelines(subprocess.Popen._execute_child)  # type: ignore[attr-defined]
        spawned = set(cov.lines(str(Path(subprocess.__file__).resolve())) or ())
        lines = set(cov.lines(str(ROOT / name)) or ())
    return lines, bool(spawned & set(range(first, first + len(src)))), wall


def _coverage(changed: dict[str, set[int]], env: dict[str, str]) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="dadaia-mutate-") as tmp:
        report = Path(tmp, "cov.json")
        _run(
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "scripts.covdata",
            "--cov", "--cov-branch", f"--cov-report=json:{report}", env=env,
        )  # fmt: skip
        files = json.loads(report.read_text("utf-8"))["files"] if report.exists() else {}
    hit = {k: 0 for k in ("lines", "all_lines", "branches", "all_branches")}
    for name, lines in changed.items():
        data = files.get(name) or files.get(str(ROOT / name)) or {}
        done, todo = data.get("executed_lines", []), data.get("missing_lines", [])
        hit["lines"] += len(lines & set(done))
        hit["all_lines"] += len(lines & set(done + todo))
        taken = sum(1 for b in data.get("executed_branches", []) if b[0] in lines)
        missed = sum(1 for b in data.get("missing_branches", []) if b[0] in lines)
        hit["branches"] += taken
        hit["all_branches"] += taken + missed
    return [
        f"diff line coverage {hit['lines']}/{hit['all_lines']}",
        f"diff branch coverage {hit['branches']}/{hit['all_branches']}",
    ]


def _matrix(home: str, ran: set[str], kills: dict[str, set[int]]) -> list[str]:
    covered = {m for t in ran if t.startswith(home) for m in kills.get(t, ())}
    others = sorted(t for t in ran if not t.startswith(home))
    deletable = [t for t in others if kills.get(t) and kills[t] <= covered]
    return [
        *(f"DELETABLE {t}" for t in deletable),
        *(f"KEPT {t}" for t in others if kills.get(t) and t not in deletable),
        *(f"NO-KILL {t}" for t in others if not kills.get(t)),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--module", nargs="+", default=[])
    parser.add_argument("--home", dest="home_id")
    parser.add_argument("--tests", nargs="+", default=[])
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    if not (args.base or args.module):
        parser.error("one of --base or --module is required")
    if _run("git", "status", "--porcelain", "--untracked-files=no").stdout.strip():
        sys.exit("refusing to mutate a dirty tree")
    changed = (
        {m: set(range(1, len((ROOT / m).read_text("utf-8").splitlines()) + 1)) for m in args.module}
        if args.module
        else changed_lines(_run("git", "diff", "-U0", "--no-color", args.base).stdout)
    )
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    killed = total = 0
    ran: set[str] = set()
    kills: dict[str, set[int]] = {}
    for name, lines in sorted(changed.items()):
        target = ROOT / name
        original = target.read_bytes()
        tests = args.tests or _tests_for(name)
        if tests:
            ran |= _test_ids(tests, env)
        executed, spawns, wall = _executed(name, tests, env) if tests else (set(), False, 0.0)
        try:
            for m in _mutants(original.decode("utf-8"), lines):
                total += 1
                label = f"{name}:{m[1]} {m[0]}: {m[4]} -> {m[5] or '(deleted)'}"
                try:
                    mutated = _apply(original.decode("utf-8"), m)
                    ast.parse(mutated)
                except SyntaxError:
                    total -= 1
                    continue
                if tests and m[1] not in executed and not spawns:
                    print(f"UNCOVERED {label}")
                    continue
                target.write_bytes(mutated.encode("utf-8"))
                try:
                    ids = _killers(tests, ran, env, max(args.timeout, 3 * wall)) if tests else None
                except subprocess.TimeoutExpired:
                    killed += 1
                    print(f"TIMEOUT {label}")
                    continue
                killed += ids is not None
                for t in ids or ():
                    kills.setdefault(t, set()).add(total)
                print(f"SURVIVED {label}" if ids is None else f"KILLED {label} [{', '.join(ids)}]")
        finally:
            target.write_bytes(original)
    print(f"mutation score {killed}/{total}")
    lines_out = _matrix(args.home_id, ran, kills) if args.home_id else []
    lines_out += [] if args.module else _coverage(changed, env)
    for line in lines_out:
        print(line)


if __name__ == "__main__":
    main()
