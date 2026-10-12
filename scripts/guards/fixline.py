"""Fix-line checks: every command the code prints or the shipped text names goes through the
one renderer and names something that exists.

``fix-lines-one-renderer`` walks every package module, skill script and tracked text file;
``fix-lines-doctor-target`` judges each doctor rule's fix; ``skill-script-fix-names-entry``
holds each skill script's fix to its folder's entry script; ``fix-line-pinned-pair`` renders
one argv through the package renderer and the scripts' ``_specs.py``. The doctor check reads
the fixes a plant's session carries under ``fixes`` instead of the live rules.
"""

from __future__ import annotations

import ast
import functools
import importlib.util
import re
import shlex
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dadaia_workspace.core import doctor_rules  # noqa: E402
from dadaia_workspace.core.cli_line import fix_line, git_line, shell_line  # noqa: E402
from dadaia_workspace.core.gitflow import DEFAULT  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Callable

    from run import Check, Plant, Session, Tree

PKG_PUBLIC = "dadaia_workspace/public"
_SKILLS_REL = f"{PKG_PUBLIC}/skills"
_PUBLIC_SKILLS = ROOT / _SKILLS_REL
#: The builder module: the one place the CLI is spelled by hand.
_BUILDER = "dadaia_workspace/core/cli_line.py"


def _defect(fix: str) -> bool:
    home = importlib.import_module("tests.core.test_cli_line__fix_line_contract")
    return bool(home.fix_defect(fix))


@functools.cache
def _cli_root() -> Any:
    import typer.main

    from dadaia_workspace.cli.main import app

    return typer.main.get_command(app)


def _cli_command(tokens: list[str]) -> Any:
    """The leaf of the live Typer tree *tokens* walk to (options stop the walk), else None."""
    cmd = _cli_root()
    for token in tokens:
        if token.startswith("-") or not getattr(cmd, "commands", None):
            break
        if token not in cmd.commands:
            return None
        cmd = cmd.commands[token]
    return (
        None
        if tokens and getattr(cmd, "commands", None) and not cmd.invoke_without_command
        else cmd
    )


# --- fix-lines-one-renderer ---------------------------------------------------------------

#: A fix callee: a `cli_line` builder's or a fix producer's arguments are fix text.
_FIX_CALL_RE = re.compile(r"(_line|_fix|^script)$")
#: A hand-built CLI spelling in a fix.
_SPELLING = re.compile(r"\.dadaia[/\\]\.venv|(?<![\w./-])dadaia\s|shlex\.")
_HAND_BUILT = {"DADAIA_BIN", "cli_path"}
#: A fix's positional index in a constructor no `def` declares.
_FIX_CTORS = {"Step": 3, "Refusal": 1, "_ledger.finding": 4}
#: A value bound to, or returned by, a `fix`-named name.
_FIX_NAME = re.compile(r"(?i)(?:^|_)fix(?:es)?(?:$|_)")
#: A builder spelling a command inside error prose with no `fix:` line, keyed on the
#: stripped source line, never its number.
_PROSE = {
    ("dadaia_workspace/cli/_specs_resolution.py",
     "f\"'{fix_line(None, 'context', 'bind', '<name>')}' in this session or pass \""),
    ("dadaia_workspace/core/invocation.py",
     "f\"`{fix_line(None, 'context', 'bind', '<name>')}`.\""),
}  # fmt: skip
#: A command line spelling the CLI — a code span or a fenced line naming it.
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_CLI_WORDS = re.compile(r"(?:^|(?<=[\s(]))(\S*(?<![\w-])dadaia)(?![\w.-])((?: [^\s|;&`]+)*)")
_DEAD_RELEASE_VOCABULARY = re.compile(r"rc-archive|release\.py (fold|archive)|rc-N|resolve` carrying")  # fmt: skip
_NON_AUTHORITY_DONE = re.compile(r"memory\.py check`? exit 0")


def _callee(node: ast.Call) -> str:
    return getattr(node.func, "id", getattr(node.func, "attr", ""))


def _render(
    node: Any, scope: dict[str, list[Any]], returns: dict[str, list[Any]], depth: int = 0
) -> str:
    """The text *node* can print; alternatives and unknown values join as `·`; a
    hand-built CLI name renders as the spelling it builds."""

    def again(n: Any) -> str:
        return _render(n, scope, returns, depth + 1) if depth < 12 else "·"

    match node:
        case ast.Constant(value=str() as text):
            return text
        case ast.Call(func=ast.Attribute(value=ast.Name(id="shlex"), attr=attr)):  # POSIX-only
            return "shlex." if attr in ("join", "quote") else "·"
        case ast.Name(id=name) | ast.Attribute(attr=name) | ast.Call(func=ast.Name(id=name)) if name in _HAND_BUILT:  # fmt: skip
            return ".dadaia/.venv "
        case ast.JoinedStr(values=parts):
            return "".join(map(again, parts))
        case ast.List(elts=parts) | ast.Tuple(elts=parts) | ast.Dict(values=parts) | ast.BoolOp(values=parts):  # fmt: skip
            return "·".join(map(again, parts))
        case ast.FormattedValue(value=v) | ast.Starred(value=v) | ast.Subscript(value=v):
            return again(v)
        case ast.ListComp(elt=v) | ast.GeneratorExp(elt=v) | ast.Lambda(body=v):
            return again(v)
        case ast.BinOp(left=left, right=right):
            return again(left) + again(right)
        case ast.IfExp(body=body, orelse=orelse):
            return f"{again(body)}·{again(orelse)}"
        case ast.Name(id=name):
            return "·".join(map(again, scope.get(name, []))) or "·"
        case ast.Attribute(attr=attr):  # a gitflow pattern renders its default
            return str(getattr(DEFAULT, attr, "·"))
        case ast.Call(func=ast.Attribute(attr="join"), args=[arg]):
            return again(arg)
        case ast.Call(func=ast.Attribute(attr="get", value=table)):  # a fix table's lookup
            return again(table)
        case ast.Call(func=ast.Attribute(value=receiver)) if not isinstance(receiver, ast.Name):
            return again(receiver)
        case ast.Call() if _callee(node) in returns:  # a local producer: what it returns
            return "·".join(map(again, returns[_callee(node)]))
        case ast.Call() if _FIX_CALL_RE.search(_callee(node)) or _callee(node)[:1].isupper():
            return " ".join(map(again, [*node.args, *(k.value for k in node.keywords)]))
    return "·"


def _scope(
    node: Any, outer: dict[str, list[Any]], walk: Callable[[Any], tuple[Any, ...]]
) -> dict[str, list[Any]]:
    """Every value a name is bound to in *node*: its defaults and assignments, then *outer*'s."""
    bound: dict[str, list[Any]] = {}
    if isinstance(node, ast.FunctionDef):
        args = node.args
        named = [*args.args[len(args.args) - len(args.defaults) :], *args.kwonlyargs]
        for arg, default in zip(named, [*args.defaults, *args.kw_defaults], strict=True):
            bound[arg.arg] = [default]
    for child in walk(node):
        if isinstance(child, ast.Assign):
            for name in (n for t in child.targets for n in ast.walk(t) if isinstance(n, ast.Name)):
                bound.setdefault(name.id, []).append(child.value)
    return {**outer, **bound}


def _code_sites(trees: dict[str, ast.Module], read: Callable[[str], str]) -> dict[str, str]:
    """``file:line`` -> kind of each fix a module can print that is not one command through
    the one renderer: ``hand-built`` (a hand-built CLI spelling), ``not-one-act`` (a `<…>`, an
    `&&`, an `a|b` menu) or ``instruction`` (a non-docstring literal telling the reader to
    run `dadaia <verb>`). Not seen: a helper's return in another module, `str.format`,
    `print("fix:", x)` with separate arguments, a returned dict literal."""
    from dadaia_workspace.cli.help_digest import command_paths

    _walk: Callable[[Any], tuple[Any, ...]] = functools.cache(lambda n: tuple(ast.walk(n)))
    verbs = "|".join(sorted({path[0] for path in command_paths() if path}))
    instruction = re.compile(rf"(?:['`]|\$\(|\b[Rr]e-?run:? |\b[Rr]un:? |\bwith |\buntil |\bthen )dadaia ({verbs})\b")  # fmt: skip

    def fix_params(owners: Any) -> dict[str, int]:
        """Each callable taking `fix` (a class: its __init__), and its position."""
        return {
            (owner.name if fn.name == "__init__" else fn.name): names.index("fix")
            for owner in owners
            for fn in (owner.body if isinstance(owner, ast.ClassDef) else [owner])
            if isinstance(fn, ast.FunctionDef)
            and "fix" in (names := [a.arg for a in fn.args.args if a.arg != "self"])
        }

    local = {rel: fix_params(_walk(t)) for rel, t in trees.items()}
    every = {**_FIX_CTORS, **{n: at for params in local.values() for n, at in params.items()}}
    every |= {f"{PurePosixPath(rel).stem}.{n}": at for rel, params in local.items() for n, at in params.items()}  # fmt: skip
    sites: dict[str, str] = {}
    for rel, tree in trees.items():
        defs = {n.name: n for n in _walk(tree) if isinstance(n, ast.FunctionDef)}
        # a local `def` wins its name, even one with no `fix` parameter
        fix_param = {**{n: at for n, at in every.items() if n not in defs}, **local[rel]}
        returns = {name: [r.value for r in _walk(d) if isinstance(r, ast.Return) and r.value] for name, d in defs.items()}  # fmt: skip
        docs = {id(n.body[0].value) for n in _walk(tree)
                if isinstance(n, ast.Module | ast.FunctionDef | ast.ClassDef) and n.body
                and isinstance(n.body[0], ast.Expr)}  # fmt: skip
        spelled = rel == _BUILDER or "/public/" in rel  # stdlib scripts spell via `_specs`
        module = _scope(tree, {}, _walk)
        for unit in [tree, *defs.values()]:
            scope = module if unit is tree else _scope(unit, module, _walk)
            for node in _walk(unit):
                fixes: list[str] = []
                if isinstance(node, ast.Call):
                    owner = getattr(node.func, "value", None)
                    qualified = f"{owner.id}.{_callee(node)}" if isinstance(owner, ast.Name) else ""
                    at = fix_param.get(qualified, fix_param.get(_callee(node), -1))
                    carried = [*node.args[at : at + 1 if at >= 0 else 0],
                               *(k.value for k in node.keywords if k.arg in ("fix", "fix_help"))]  # fmt: skip
                    if _FIX_CALL_RE.search(_callee(node)):
                        carried.append(node)
                    fixes = [_render(c, scope, returns) for c in carried]
                elif (
                    isinstance(node, ast.Constant | ast.JoinedStr | ast.BinOp)
                    and id(node) not in docs
                ):
                    fixes = _render(node, scope, returns).split("fix: ")[1:]
                elif isinstance(node, ast.Assign | ast.AnnAssign) and node.value is not None:
                    names = [
                        ast.unparse(t)
                        for t in (node.targets if isinstance(node, ast.Assign) else [node.target])
                    ]
                    fixes = (
                        [_render(node.value, scope, returns)]
                        if any(map(_FIX_NAME.search, names))
                        else []
                    )
                elif isinstance(node, ast.FunctionDef) and _FIX_NAME.search(node.name):
                    fixes = [
                        _render(r.value, scope, returns)
                        for r in _walk(node)
                        if isinstance(r, ast.Return) and r.value
                    ]
                text = getattr(node, "value", None) if isinstance(node, ast.Constant) else None
                told = isinstance(text, str) and id(node) not in docs and instruction.search(text)
                # a value carrying its own message keeps only what follows its `fix: `
                alts = [a.strip() for f in fixes for a in f.split("fix: ")[1:] or [f] if a.strip()]
                hand = not spelled and any(_SPELLING.search(a) for a in alts)
                kind = (
                    "hand-built"
                    if hand
                    else "not-one-act"
                    if any(map(_defect, alts))
                    else ("instruction" if told and rel != _BUILDER else "")
                )
                if kind:
                    sites.setdefault(f"{rel}:{node.lineno}", kind)
    prose = {r for r, _ in _PROSE}
    return {
        site: kind
        for site, kind in sites.items()
        if (rel := site.rsplit(":", 1)[0]) not in prose
        or (rel, read(rel).splitlines()[int(site.rsplit(":", 1)[1]) - 1].strip()) not in _PROSE
    }


def _bad_command(text: str) -> bool:
    """A bare `dadaia <verb>`, `$DADAIA_BIN`, or a venv CLI line whose verb or flag the
    live command tree lacks."""
    if "$DADAIA_BIN" in text:
        return True
    for match in _CLI_WORDS.finditer(text):
        head, words = match.group(1), match.group(2).split()
        if head == "dadaia" and words and words[0] in _cli_root().commands:
            return True
        if head.endswith(".venv/bin/dadaia"):
            cmd = _cli_command(words)
            flags = {w.split("=")[0] for w in words if w.startswith("--")} - {"--help"}
            if cmd is None or flags - {o for p in cmd.params for o in p.opts}:
                return True
    return False


def _text_rows(rel: str) -> list[tuple[str, Callable[[str], object]]]:
    """The named scans a tracked text file's lines take, by where it ships: the law and the
    shipped surface name no retired verb; what ships names no `memory.py check` done
    criterion; the getting-started page no release-please; `public/**/*.md` command lines
    spell the live CLI; a public script's git fix goes through `_specs.git_line`."""
    rows: list[tuple[str, Callable[[str], object]]] = []
    if rel.startswith((f"{PKG_PUBLIC}/", "specs/memory/")) or rel == "CONTEXT.md":
        rows.append(("dead-vocabulary", _DEAD_RELEASE_VOCABULARY.search))
    if not rel.startswith("specs/"):
        rows.append(("done-criterion", _NON_AUTHORITY_DONE.search))
    if rel == "docs/getting-started.md":
        rows.append(("release-please", re.compile("release-please").search))
    if rel.startswith(f"{PKG_PUBLIC}/") and rel.endswith(".md"):
        rows.append(("bad-command", lambda line: any(_bad_command(s) for s in _CODE_SPAN.findall(line))))  # fmt: skip
    if rel.startswith(f"{PKG_PUBLIC}/") and rel.endswith(".py"):
        rows.append(("hand-git", re.compile(r"git -C \{").search))
    return rows


def fix_lines_one_renderer(tree: Tree) -> list[str]:
    """Each fix the package prints and each command line the shipped text holds that bypasses
    the one renderer or names a verb the live CLI lacks."""
    listed = [
        rel
        for rel in tree.tracked("dadaia_workspace", "specs/memory", "CONTEXT.md", "docs")
        if "_archive" not in rel
    ]
    code = {rel: ast.parse(tree.read(rel)) for rel in listed if rel.endswith(".py")}
    found = [f"{kind}: {site}" for site, kind in sorted(_code_sites(code, tree.read).items())]
    for rel in listed:
        if rel.startswith(("dadaia_workspace/", "docs/")) and not (
            rel.startswith(f"{PKG_PUBLIC}/") or rel.endswith(".md")
        ):
            continue
        rows, fenced = _text_rows(rel), False
        for number, line in enumerate(tree.read(rel).splitlines(), start=1):
            fenced ^= line.startswith("```")
            if fenced and rel.startswith(f"{PKG_PUBLIC}/") and _bad_command(line):
                found.append(f"bad-command: {rel}:{number}")
            found += [f"{name}: {rel}:{number}" for name, row in rows if row(line)]
    return found


# --- fix-lines-doctor-target --------------------------------------------------------------

#: The installed skill tree maps to the `public/skills/` source.
_INSTALLED_SKILL_PREFIX = ".agents/skills/"
_VENV_PYTHON = Path(sys.executable).as_posix()
_SKILLS = _PUBLIC_SKILLS.as_posix() + "/"
_FLAG_VALUE_RE = re.compile(r"^--[\w-]+=")


def _live_rule_fixes() -> list[tuple[str, str]]:
    from dadaia_workspace.features.backlog.doctor import RULES as BACKLOG_RULES
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.doctor_adr import LEDGER_RULES
    from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES

    rules: list[doctor_rules.Rule[Any]] = [
        *workspace_rules(expired_only=False),
        *SPECS_RULES,
        *BACKLOG_RULES,
        *LEDGER_RULES,
    ]
    return [
        ("/".join(rule.codes), doctor_rules.rule_fix(rule, Path(), Path("specs")))
        for rule in rules
        if rule.fix_help
    ]


def _known_dirs(tree: Tree) -> frozenset[str]:
    """Every directory the tree tracks, plus the ones the specs canon guarantees."""
    from dadaia_workspace.core.workspace_layout import SPECS_CANON

    tracked = (PurePosixPath(t).parts for t in tree.tracked())
    dirs = {PurePosixPath(*p[:d]).as_posix() for p in tracked for d in range(1, len(p))}
    canon = (PurePosixPath(entry.shape).parts for entry in SPECS_CANON)
    return frozenset(dirs | {PurePosixPath("specs", *p[:d]).as_posix() for p in canon for d in range(len(p))} | {""})  # fmt: skip


def _unresolved_paths(command: str, known: frozenset[str]) -> list[str]:
    """Every unquoted path token (a slash; a ``--flag=value`` carries it in the value) whose
    directory is neither tracked nor guaranteed by the specs canon: a fix creates, edits or
    deletes its leaf, so only the directory holding it must exist."""
    lexer = shlex.shlex(command, posix=False)
    lexer.whitespace_split = True
    unresolved: list[str] = []
    for raw in lexer:
        token = _FLAG_VALUE_RE.sub("", raw.removeprefix(ROOT.as_posix() + "/"))
        if raw == _VENV_PYTHON or token.startswith((".dadaia/", "'", '"', "-", ">", "&", "|")):
            continue  # the interpreter, the venv binary (the CLI arm), a quoted script
        if "/" not in token:
            continue
        if token.startswith(_INSTALLED_SKILL_PREFIX):
            token = f"{PKG_PUBLIC}/skills/" + token.removeprefix(_INSTALLED_SKILL_PREFIX)
        if PurePosixPath(token).parent.as_posix().removesuffix(".") not in known:
            unresolved.append(token)
    return unresolved


def fix_lines_doctor_target(tree: Tree) -> list[str]:
    """Each doctor rule's fix is one act, names a directory that exists, runs a verb the
    live CLI has, and a skill-script fix runs a shipped script whose subcommand takes ``--help``."""
    injected = (tree._session or {}).get("fixes")
    fixes = _live_rule_fixes() if injected is None else injected
    known, found = _known_dirs(tree), []
    for codes, command in fixes:
        if _defect(command) or "<specs>" in command:
            found.append(f"not-one-act: {codes}: {command!r}")
        found += [f"unresolved-path: {codes}: {t}" for t in _unresolved_paths(command, known)]
        tokens = shlex.split(command)
        if command.startswith(fix_line(Path())) and not _cli_command(tokens[1:]):
            found.append(f"no-such-verb: {codes}: {command!r}")
        if "/scripts/" not in command:
            continue
        if not (tokens[0] == _VENV_PYTHON and tokens[1].startswith(_SKILLS) and Path(tokens[1]).is_file()):  # fmt: skip
            found.append(f"not-a-shipped-script: {codes}: {command!r}")
            continue
        verb = next(t for t in tokens[2:] if not t.startswith("-"))
        help_run = subprocess.run([sys.executable, tokens[1], verb, "--help"],
                                  capture_output=True, text=True, encoding="utf-8", timeout=60)  # fmt: skip
        if help_run.returncode:
            found.append(f"script-rejects-verb: {codes}: {tokens[1]} {verb}")
    return found


# --- skill-script-fix-names-entry ---------------------------------------------------------

#: The one entry script of each skill that ships scripts — what an operator pastes.
_ENTRY_SCRIPTS: dict[str, str] = {
    "dd-audit-project": "audit.py",
    "dd-backlog-definition": "backlog.py",
    "dd-bug-resolution": "bugs.py",
    "dd-cli-library": "registry.py",
    "dd-handoff-emitter": "verdict.py",
    "dd-gitflow-default": "worktree.py",
    "dd-release-implementation": "release.py",
    "dd-spec-navigator": "memory.py",
}
_LITERAL_FIX_RE = re.compile(r'"fix: ([^"]*)')
_SCRIPT_CONST_RE = re.compile(r'^SCRIPT = Path\(__file__\)\.parent / "([^"]+)"', re.MULTILINE)
_NAMED_SCRIPT_RE = re.compile(r"[\w.{}\[\]()/-]*\.py")


def skill_script_fix_names_entry(tree: Tree) -> list[str]:
    """Every `fix:` literal naming a `.py` file, and every ``SCRIPT`` constant a refusal fix
    is built from, names its folder's entry script — never a sibling module with no
    ``__main__``."""
    found = []
    for rel in tree.tracked(_SKILLS_REL):
        parts = PurePosixPath(rel).parts
        if not (rel.endswith(".py") and len(parts) == 6 and parts[-2] == "scripts"):
            continue
        entry, text = _ENTRY_SCRIPTS.get(parts[-3], ""), tree.read(rel)
        if not entry:
            found.append(f"unknown-skill: {rel}")
        for body in _LITERAL_FIX_RE.findall(text):
            if "__file__" in body:
                found.append(f"file-reference: {rel}: {body!r}")
            if not all(n.endswith(entry) for n in _NAMED_SCRIPT_RE.findall(body)):
                found.append(f"sibling-script: {rel}: {body!r}")
        found += [f"script-constant: {rel}: {n!r}" for n in _SCRIPT_CONST_RE.findall(text) if n != entry]  # fmt: skip
    return found


# --- fix-line-pinned-pair -----------------------------------------------------------------

_SPECS_REL = f"{_SKILLS_REL}/dd-bug-resolution/scripts/_specs.py"


def fix_line_pinned_pair(tree: Tree) -> list[str]:
    """One argv through ``core/cli_line`` and the scripts' ``_specs.py`` renders one line — a
    blank, a quote and a ``$`` included, the interpreter head's too."""
    path = tree.root / _SPECS_REL
    if not path.is_file():
        return [f"missing: {_SPECS_REL}"]
    saved = sys.executable
    sys.executable = str(Path("/tmp/Program Files (x86)/python"))  # a blank in the head
    sys.path.insert(0, str(path.parent))
    try:
        loader = importlib.util.spec_from_file_location("_specs_pinned", path)
        assert loader and loader.loader
        specs = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(specs)
        rest = ["commit", "-m", "it's $HOME"]
        found = []
        if specs.git_line(Path("/a b"), *rest) != git_line(Path("/a b"), *rest):
            found.append("git-line: _specs.git_line renders an argv differently from cli_line")
        script = Path("/s p/x.py")
        if specs.script(script) != shell_line(sys.executable, str(script.resolve())):
            found.append("script: _specs.script renders an argv differently from cli_line")
        return found
    finally:
        sys.executable = saved
        sys.path.remove(str(path.parent))


# --- plants -------------------------------------------------------------------------------


def _write(root: Path, rel: str, text: str) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")


_CLEAN_FIX = "sed -i 's/x/y/g' specs/bugs/BUGS.jsonl"
_CLEAN_CODE = 'fix = git_line(repo, "switch", work)\nOK = "fix: Operator action: open the PR"\n'


def CONTROL(root: Path) -> Session:
    """Every check green: clean siblings tracked, the same violations in an untracked,
    gitignored file, and a doctor fix that resolves."""
    _write(root, ".gitignore", "scratch/\n")
    _write(root, "scratch/m.py", 'Y = "fix: release.py ship --pr <n>"\n')
    _write(root, "dadaia_workspace/m.py", _CLEAN_CODE)
    _write(root, "dadaia_workspace/public/skills/dd-bug-resolution/scripts/x.py",
           'F = "fix: git status"\n')  # fmt: skip
    _write(root, _SPECS_REL, (ROOT / _SPECS_REL).read_text(encoding="utf-8"))
    return {"fixes": [("CTRL", _CLEAN_FIX)]}


def _file(rel: str, text: str) -> Plant:
    def plant(root: Path) -> Session:
        session = CONTROL(root)
        _write(root, rel, text)
        return session

    return plant


def _fixes(*commands: str) -> Plant:
    def plant(root: Path) -> Session:
        CONTROL(root)
        return {"fixes": [("ZZ", c) for c in commands]}

    return plant


def _skill(text: str) -> Plant:
    return _file("dadaia_workspace/public/skills/dd-bug-resolution/scripts/x.py", text)


def _specs(old: str, new: str) -> Plant:
    return _file(_SPECS_REL, (ROOT / _SPECS_REL).read_text(encoding="utf-8").replace(old, new, 1))


_PLANTS: dict[str, dict[str, Plant]] = {
    "fix-lines-one-renderer": {
        "hand-built": _file("dadaia_workspace/m.py", 'X = f"fix: {DADAIA_BIN} doctor"\n'),
        "not-one-act": _file("dadaia_workspace/m.py", 'Y = "fix: release.py ship --pr <n>"\n'),
        "instruction": _file("dadaia_workspace/m.py", 'Z = "Run: dadaia doctor"\n'),
        "dead-vocabulary": _file("dadaia_workspace/public/x.md", "the `rc-archive` verb\n"),
        "done-criterion": _file("docs/x.md", "done when `memory.py check` exit 0\n"),
        "release-please": _file("docs/getting-started.md", "release-please\n"),
        "bad-command": _file(
            "dadaia_workspace/public/x.md", "`.dadaia/.venv/bin/dadaia doctor --nosuchflag`\n"
        ),
        "hand-git": _file("dadaia_workspace/public/s.py", 'fix = f"git -C {repo} switch {work}"\n'),
    },
    "fix-lines-doctor-target": {
        "not-one-act": _fixes("git rm <x> && git add ."),
        "unresolved-path": _fixes("git rm dadaia_workspace/features/no_such_feature/doctor.py"),
        "no-such-verb": _fixes(fix_line(Path(), "nosuchverb")),
        "not-a-shipped-script": _fixes(f"{_VENV_PYTHON} /elsewhere/scripts/x.py run"),
    },
    "skill-script-fix-names-entry": {
        "sibling-script": _skill('F = "fix: python _ledger.py check"\n'),
        "file-reference": _skill('F = "fix: python __file__ check"\n'),
        "script-constant": _skill('SCRIPT = Path(__file__).parent / "_ledger.py"\n'),
        "unknown-skill": _file(f"{_SKILLS_REL}/dd-zz/scripts/x.py", "X = 1\n"),
    },
    "fix-line-pinned-pair": {
        "git-line": _specs(
            '" ".join(map(quote, ("git", "-C", str(repo), *argv)))',
            '" ".join(("git", "-C", str(repo), *argv))',
        ),  # fmt: skip
        "script": _specs(
            'return f"{head(sys.executable)} {quote(str(path.resolve()))}"',
            'return f"{sys.executable} {path.resolve()}"',
        ),  # fmt: skip
    },
}
CHECKS: dict[str, Check] = {
    cid: (globals()[cid.replace("-", "_")], rows) for cid, rows in _PLANTS.items()
}
