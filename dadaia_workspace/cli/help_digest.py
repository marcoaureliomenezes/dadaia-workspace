"""Derived CLI help digest — generated from the live command tree, never transcribed.

Backlog `cli-help-architecture-and-session-injection` (operator request 2026-08-23,
docker/cobra model): the hand-written CLI skill was structurally condemned to rot
(ghost verbs, 53% coverage). The digest is introspected from the Typer/Click tree —
ONE source — written under ``.dadaia/agentic/`` by ``public install``
and ``reconcile`` (NEVER at hook fire: hooks read the file, they never build it), and
attached to every ctx-inject emission bind-independent.
"""

from __future__ import annotations

import functools
from pathlib import Path

__all__ = ["DIGEST_REL", "command_paths", "digest_path", "render_digest", "write_digest"]

#: Workspace-relative location of the digest (projected state, not a public/ asset).
DIGEST_REL = Path(".dadaia") / "agentic" / "help-digest.md"

#: Hard budget for the rendered digest (~4k tokens; the full --help dump measures
#: ~33.5k tokens and is unusable as an injection payload).
_MAX_CHARS = 16_000
#: Emitted by the generator itself, so `.dadaia/.venv/bin/dadaia help tree > docs/cli.md`
#: reproduces the committed file byte-for-byte — the regenerate line names a command that is true.
_HEADER = (
    "<!-- derived-from: dadaia help tree — regenerate: "
    "`.dadaia/.venv/bin/dadaia help tree > docs/cli.md` -->"
)


def _first_line(text: str | None) -> str:
    return (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""


def _root_command() -> object:
    """The live Typer app as a click-compatible root command.

    Imported, never a subprocess ``--help`` parse: hermetic, fast and always in sync
    with the tree this process ships.
    """
    from typer.main import get_command

    from dadaia_workspace.cli.main import app  # lazy: avoid an import cycle

    return get_command(app)


@functools.lru_cache(maxsize=1)
def command_paths() -> frozenset[tuple[str, ...]]:
    """Every command path of the live tree, root ``()`` included — walked ONCE per
    process (0.4.7 FR2: the digest, the citation contract tests and the doctor's
    ``MEM-DRIFT-2`` share this one walk).

    Walked by duck-typing (``hasattr(cmd, "commands")``), never ``isinstance(cmd,
    click.Group)``: the installed ``typer`` (``>=0.27.1``) vendors its own
    click-compatible core (``typer._click.core``), so ``typer.core.TyperGroup`` does NOT
    subclass the external ``click.Group`` — an ``isinstance`` check silently walks zero
    children. Duck-typing is the version-robust choice across typer/click pairings.
    """
    paths: set[tuple[str, ...]] = {()}

    def _walk(cmd: object, prefix: tuple[str, ...]) -> None:
        commands = getattr(cmd, "commands", None)
        if not isinstance(commands, dict):
            return
        for name, sub in commands.items():
            child = prefix + (name,)
            paths.add(child)
            _walk(sub, child)

    _walk(_root_command(), ())
    return frozenset(paths)


def render_digest() -> str:
    """Introspect the live command tree into a compact, stamped digest."""
    root = _root_command()
    # Duck-typed group detection: this typer version ships its own click shim
    # (typer._click), so isinstance against the click package is unreliable.
    root_commands: dict[str, object] = dict(getattr(root, "commands", {}) or {})
    assert root_commands, "command-tree introspection found no commands"
    lines: list[str] = [
        _HEADER,
        "",
        "# dadaia CLI digest (derived from the live command tree; "
        "authoritative help: `dadaia <group> --help`)",
        "",
    ]
    for name in sorted(root_commands):
        cmd = root_commands[name]
        subs = dict(getattr(cmd, "commands", {}) or {})
        if subs:
            lines.append(f"## dadaia {name} — {_first_line(getattr(cmd, 'help', None))}")
            for sub_name in sorted(subs):
                sub = subs[sub_name]
                nested = dict(getattr(sub, "commands", {}) or {})
                if nested:
                    inner = ", ".join(sorted(nested))
                    lines.append(
                        f"- {name} {sub_name} <{inner}> — {_first_line(getattr(sub, 'help', None))}"
                    )
                else:
                    lines.append(f"- {name} {sub_name} — {_first_line(getattr(sub, 'help', None))}")
        else:
            lines.append(f"## dadaia {name} — {_first_line(getattr(cmd, 'help', None))}")
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    if len(text) > _MAX_CHARS:  # keep the budget honest: trim whole trailing lines
        text = text[:_MAX_CHARS].rsplit("\n", 1)[0] + "\n[digest truncated at budget]\n"
    return text


def digest_path(workspace_root: Path) -> Path:
    return workspace_root / DIGEST_REL


def write_digest(workspace_root: Path) -> Path | None:
    """Write the digest, skipping when the file already holds exactly this digest.

    Fail-soft: any error returns ``None`` — regeneration is a convenience rider on
    install/reconcile, never a reason to fail them.
    """
    try:
        path = digest_path(workspace_root)
        text = render_digest()
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
    except Exception:  # noqa: BLE001 — advisory artifact only
        return None
