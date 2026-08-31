"""Derived CLI help digest — generated from the live command tree, never transcribed.

Backlog `cli-help-architecture-and-session-injection` (operator request 2026-08-23,
docker/cobra model): the hand-written CLI skill was structurally condemned to rot
(ghost verbs, 53% coverage). The digest is introspected from the Typer/Click tree —
ONE source — version-stamped, written under ``.dadaia/agentic/`` by ``public install``
and ``reconcile`` (NEVER at hook fire: hooks read the file, they never build it), and
attached to every ctx-inject emission bind-independent.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["DIGEST_REL", "digest_path", "render_digest", "write_digest"]

#: Workspace-relative location of the digest (projected state, not a public/ asset).
DIGEST_REL = Path(".dadaia") / "agentic" / "help-digest.md"

#: Hard budget for the rendered digest (~4k tokens; the full --help dump measures
#: ~33.5k tokens and is unusable as an injection payload).
_MAX_CHARS = 16_000


def _version() -> str:
    from importlib import metadata

    try:
        return metadata.version("dadaia-workspace")
    except metadata.PackageNotFoundError:
        return "0+source"


def _first_line(text: str | None) -> str:
    return (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""


def render_digest() -> str:
    """Introspect the live command tree into a compact, stamped digest."""
    from typer.main import get_command

    from dadaia_workspace.cli.main import app  # lazy: avoid an import cycle

    root = get_command(app)
    # Duck-typed group detection: this typer version ships its own click shim
    # (typer._click), so isinstance against the click package is unreliable.
    root_commands: dict[str, object] = dict(getattr(root, "commands", {}) or {})
    assert root_commands, "command-tree introspection found no commands"
    lines: list[str] = [
        f"# dadaia CLI digest (v{_version()} — derived from the live command tree; "
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
    """Write the digest, skipping when the on-disk stamp already matches this version.

    Fail-soft: any error returns ``None`` — regeneration is a convenience rider on
    install/reconcile, never a reason to fail them.
    """
    try:
        path = digest_path(workspace_root)
        stamp = f"(v{_version()} "
        if path.is_file() and stamp in path.read_text(encoding="utf-8")[:200]:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_digest(), encoding="utf-8")
        return path
    except Exception:  # noqa: BLE001 — advisory artifact only
        return None
