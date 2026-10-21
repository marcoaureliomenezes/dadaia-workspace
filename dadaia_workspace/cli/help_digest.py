"""Derived CLI help digest — generated from the live command tree, never transcribed.

A hand-written CLI skill rots (ghost verbs, stale coverage). The digest is introspected
from the Typer/Click tree —
ONE source — written under ``.dadaia/agentic/`` by ``public install``
and ``reconcile`` (NEVER at hook fire: hooks read the file, they never build it), and
attached to every ctx-inject emission bind-independent.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core import platform

__all__ = ["DIGEST_REL", "command_paths", "digest_path", "render_digest", "write_digest"]

#: Workspace-relative location of the digest (projected state, not a public/ asset).
DIGEST_REL = Path(".dadaia") / "agentic" / "help-digest.md"

#: Hard budget for the rendered digest (~4k tokens; the full --help dump measures
#: ~33.5k tokens and is unusable as an injection payload).
_MAX_CHARS = 16_000


def _first_line(text: str | None) -> str:
    return (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""


def command_paths(root: object) -> frozenset[tuple[str, ...]]:
    """Every command path of the tree under *root* (the click-compatible root command
    the running command received), root ``()`` included.

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

    _walk(root, ())
    return frozenset(paths)


def render_digest(root: object) -> str:
    """Introspect the command tree under *root* into a compact digest."""
    # Duck-typed group detection: this typer version ships its own click shim
    # (typer._click), so isinstance against the click package is unreliable.
    root_commands: dict[str, object] = dict(getattr(root, "commands", {}) or {})
    assert root_commands, "command-tree introspection found no commands"
    lines: list[str] = [
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


def write_digest(workspace_root: Path, root: object) -> Path | None:
    """Write the digest, skipping when the file already holds exactly this digest.

    Fail-soft: any error returns ``None`` — regeneration is a convenience rider on
    install/reconcile, never a reason to fail them.
    """
    try:
        path = digest_path(workspace_root)
        text = render_digest(root)
        if path.is_file() and platform.read_text(path) == text:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        platform.write_text(path, text)
        return path
    except Exception:  # noqa: BLE001 — advisory artifact only
        return None
