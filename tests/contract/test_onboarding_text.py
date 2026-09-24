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


def test_every_onboarding_doc_cli_line_invokes_the_venv_path() -> None:
    violations = [
        f"{doc}:{number}: `{line.strip()}`"
        for doc in _ONBOARDING_DOCS
        for number, line in _code_lines((_REPO_ROOT / doc).read_text("utf-8"))
        if _bare_invocations(line)
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
