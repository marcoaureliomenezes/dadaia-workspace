"""An act sentence holds prose, never a second label or a spelled command line."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from dadaia_workspace.cli.commands.init import InitPlan

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_SPELLERS = frozenset(
    {
        "fix_line",
        "git_line",
        "mkdir_line",
        "shell_line",
        "spell_fix",
        "reinstall_fix",
        "command",
    }
)


def _spells(node: ast.AST) -> bool:
    """Whether *node* is a call to a line speller, by bare name or attribute."""
    if not isinstance(node, ast.Call):
        return False
    fn = node.func
    return (isinstance(fn, ast.Name) and fn.id in _SPELLERS) or (
        isinstance(fn, ast.Attribute) and fn.attr in _SPELLERS
    )


def _spelled_names(scope: ast.AST) -> set[str]:
    """The names *scope* binds to a spelled line."""
    return {
        target.id
        for node in ast.walk(scope)
        if isinstance(node, ast.Assign | ast.AnnAssign | ast.NamedExpr)
        and node.value is not None
        and _spells(node.value)
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }


def _embeds_line_or_label(call: ast.Call, spelled: set[str]) -> bool:
    for arg in call.args[1:]:
        for node in ast.walk(arg):
            if _spells(node) or (isinstance(node, ast.Name) and node.id in spelled):
                return True
            if isinstance(node, ast.Constant) and "action:" in str(node.value).lower():
                return True
    return False


def _act_sentences_with_a_second_label_or_line() -> list[str]:
    hits: list[str] = []
    for path in sorted(_PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for scope in (
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        ):
            spelled = _spelled_names(scope)
            for node in ast.walk(scope):
                is_act = isinstance(node, ast.Call) and (
                    (isinstance(node.func, ast.Name) and node.func.id == "act")
                    or (isinstance(node.func, ast.Attribute) and node.func.attr == "act")
                )
                if is_act and _embeds_line_or_label(node, spelled):  # type: ignore[arg-type]
                    hits.append(f"{path.relative_to(_PKG.parent)}:{node.lineno}")
    return sorted(set(hits))


def test_no_act_sentence_embeds_a_second_label_or_a_line_speller() -> None:
    assert _act_sentences_with_a_second_label_or_line() == []


def test_init_plan_command_has_one_mode() -> None:
    assert list(inspect.signature(InitPlan.command).parameters) == ["self", "directory", "runner"]
