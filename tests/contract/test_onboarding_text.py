"""Intent: CONTRACT — AC6.4, AC7.1, T-048-10. A newcomer copies commands verbatim: every
shipped `fix:` line and every onboarding-doc CLI line invokes the workspace's own CLI by
its venv path (`.dadaia/.venv/bin/dadaia`), the one exception being the
`uvx dadaia-workspace init` bootstrap that creates that venv; no shipped text names the
retired "repos catalog"."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE = _REPO_ROOT / "dadaia_workspace"
_ONBOARDING_DOCS = (
    "README.md",
    "llms.txt",
    "docs/quickstart.md",
    "docs/getting-started.md",
    "docs/index.md",
)
_FIX_KEYWORDS = frozenset({"fix", "fix_help"})
# A bare `dadaia`/`dadaia-workspace` command word: not preceded by a path separator,
# a dot or a word character (so `.venv/bin/dadaia` and `dadaia_workspace` pass).
_BARE_CLI_RE = re.compile(r"(?<![\w./-])dadaia(?:-workspace)?(?= [a-z-])")
_UVX_INIT_RE = re.compile(r"uvx dadaia-workspace(?:@\S+)? init\b")
_FENCE_RE = re.compile(r"^```")


def _render(node: ast.expr) -> str | None:
    """A string literal's text; an f-string with each placeholder shown as `{…}`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(str(v.value) if isinstance(v, ast.Constant) else "{}" for v in node.values)
    return None


def _fix_literals(path: Path) -> list[tuple[int, str]]:
    """Every `fix:` literal in a module: the text after `fix: ` in any string, plus the
    value of every `fix=`/`fix_help=` keyword argument."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if isinstance(node, ast.keyword) and node.arg in _FIX_KEYWORDS:
            text = _render(node.value)
            if text is not None:
                found.append((node.value.lineno, text))
        elif isinstance(node, (ast.Constant, ast.JoinedStr)):
            text = _render(node)
            if text is not None and "fix: " in text:
                found.append((node.lineno, text.split("fix: ", 1)[1]))
    return found


def _bare_invocations(line: str) -> list[str]:
    stripped = _UVX_INIT_RE.sub("", line)
    return [m.group(0) for m in _BARE_CLI_RE.finditer(stripped)]


def test_every_shipped_fix_line_invokes_the_cli_by_its_venv_path() -> None:
    violations = [
        f"{path.relative_to(_REPO_ROOT).as_posix()}:{lineno}: fix: {text.strip()[:80]}"
        for path in sorted(_PACKAGE.rglob("*.py"))
        for lineno, text in _fix_literals(path)
        if _bare_invocations(text)
    ]
    assert violations == [], "\n".join(violations)


def _code_lines(text: str) -> list[tuple[int, str]]:
    """Lines inside fenced blocks and inline backtick spans — what a reader copies."""
    lines: list[tuple[int, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line.strip()):
            fenced = not fenced
            continue
        if fenced:
            lines.append((number, line))
        else:
            lines.extend((number, span) for span in re.findall(r"`([^`]+)`", line))
    return lines


# The one exempt span: the provenance banner is a fixed literal that
# `infrastructure/workspace_guardrail.py` matches byte-for-byte to recognise a projected
# AGENTS.md; rewording it would orphan every copy already projected.
_BANNER_SPAN = ("dadaia_workspace/public/data/AGENTS.md", 2)


def _shipped_text() -> list[Path]:
    public = _PACKAGE / "public"
    return sorted(
        {
            *public.rglob("*.md"),
            *public.rglob("*.txt"),
            *(_REPO_ROOT / "docs").glob("*.md"),
            *(_REPO_ROOT / name for name in ("README.md", "llms.txt", "CONTEXT.md")),
        }
    )


def test_all_shipped_text_invokes_the_cli_by_its_venv_path() -> None:
    """Intent: CONTRACT — shipped-text-cites-bare-dadaia-the-gate-blocks. Backticked spans
    and fences are what an agent copies; prose naming the product (`dadaia-workspace`,
    "the dadaia CLI") is outside them and stays free. Zero tolerance."""
    violations = [
        f"{name}:{n}: `{line.strip()}`"
        for path in _shipped_text()
        for name in [path.relative_to(_REPO_ROOT).as_posix()]
        for n, line in _code_lines(path.read_text("utf-8"))
        if _bare_invocations(line) and (name, n) != _BANNER_SPAN
    ]
    assert violations == [], "\n".join(violations)


def test_no_shipped_text_names_the_repos_catalog() -> None:
    shipped = [
        *(_REPO_ROOT / doc for doc in _ONBOARDING_DOCS),
        *sorted((_REPO_ROOT / "docs").glob("*.md")),
        *(
            p
            for p in sorted(_PACKAGE.rglob("*"))
            if p.is_file() and p.suffix in {".py", ".md", ".txt", ".json", ".sh"}
        ),
    ]
    violations = sorted(
        {
            p.relative_to(_REPO_ROOT).as_posix()
            for p in shipped
            if re.search(r"repos catalog", p.read_text("utf-8", errors="replace"), re.IGNORECASE)
        }
    )
    assert violations == [], "\n".join(violations)


def test_the_detector_flags_bare_calls_and_spares_the_venv_path_and_uvx_init() -> None:
    assert _bare_invocations("dadaia doctor --fix") == ["dadaia"]
    assert _bare_invocations("run dadaia-workspace init x") == ["dadaia-workspace"]
    assert _bare_invocations(".dadaia/.venv/bin/dadaia doctor") == []
    assert _bare_invocations("/w/.dadaia/.venv/bin/dadaia context list") == []
    assert _bare_invocations("uvx dadaia-workspace init demo --repo x") == []
    assert _bare_invocations("uvx dadaia-workspace@0.4.8 init demo") == []
    assert _bare_invocations("{} context list") == []


_VENV_CALL_RE = re.compile(r"\.dadaia/\.venv/bin/dadaia((?: [a-z][\w-]*)+)([^`]*)")
_FLAG_RE = re.compile(r"(?<![\w-])--[a-z][\w-]*")


def _cli_tree() -> dict[str, set[str]]:
    """Every command path (`context bind`) mapped to the flags it accepts."""
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
    words, path = match.group(1).split(), ""
    for word in words:
        if f"{path} {word}".strip() not in tree:
            break
        path = f"{path} {word}".strip()
    return [f for f in _FLAG_RE.findall(match.group(0)) if f not in tree[path]]


def test_every_flag_cited_beside_a_venv_call_exists_in_that_verbs_help() -> None:
    """Intent: CONTRACT — dd-cli-library-cites-a-dead-flag-and-omits-level-3. A flag the
    law or a skill cites next to `.dadaia/.venv/bin/dadaia <verb>` is one that verb takes;
    the dd-cli-library core idioms cite no flag the CLI tree lacks."""
    tree = _cli_tree()
    every_flag = set().union(*tree.values())
    public = _PACKAGE / "public"
    violations = [
        f"{path.relative_to(public).as_posix()}:{n}: {dead}"
        for path in sorted([*(public / "data").glob("*.md"), *(public / "skills").rglob("*.md")])
        for n, span in _code_lines(path.read_text("utf-8"))
        for dead in _dead_flags(span, tree)
    ]
    idioms = (
        (public / "skills/dd-cli-library/SKILL.md").read_text("utf-8").split("## Dev-server")[0]
    )
    violations += [
        f"dd-cli-library core idioms:{n}: {flag}"
        for n, span in _code_lines(idioms)
        if span.startswith("--")
        for flag in _FLAG_RE.findall(span)
        if flag not in every_flag
    ]
    assert violations == [], "\n".join(violations)


def test_the_cli_library_onboarding_line_names_level_3() -> None:
    """Intent: CONTRACT — dd-cli-library-cites-a-dead-flag-and-omits-level-3."""
    text = (_PACKAGE / "public/skills/dd-cli-library/SKILL.md").read_text("utf-8")
    assert "Level 3: `.dadaia/.venv/bin/dadaia specs init --context <ctx>`" in text
    assert "dd-audit-project" in text
