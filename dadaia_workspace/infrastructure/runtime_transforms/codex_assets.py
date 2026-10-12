"""Codex frontmatter-parsing and TOML/rules rendering free functions.

These functions are extracted from ``public_assets.py`` to keep that module under
600 lines.  All names remain importable from
``dadaia_workspace.infrastructure.public_assets`` via its re-export block.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.frontmatter import Frontmatter, parse
from dadaia_workspace.core.model_registry import TIER_CODEX
from dadaia_workspace.core.workspace_layout import render_registry_tables
from dadaia_workspace.infrastructure.public_assets_common import _toml_escape

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Every name/prefix here gates which backtick-quoted skill references
# ``dcx7_codex_skill_refs`` (D-CX-7) even bothers checking for existence, resolved
# against the shared ``.agents/skills/`` tree Codex reads natively (codex_doctor.py).
# Each entry must be an exact name or leading-hyphen prefix of a real
# ``public/skills/<name>/SKILL.md`` SOURCE skill. A name that resolves to nothing is a phantom
# prefix: it gates nothing real and would silently stop protecting the family it was
# meant to cover (a test derives this whole tuple from the on-disk inventory — ``tests/infrastructure/runtime_transforms/test_codex_assets.py``).
_CODEX_SKILL_REF_PREFIXES = ("dd-",)


def codex_model(alias: str) -> str:
    """The Codex model id for the tier *alias*; ``ValueError`` names an unknown alias."""
    if alias not in TIER_CODEX:
        raise ValueError(f"No Codex mapping for model alias: {alias!r}")
    return TIER_CODEX[alias]


# ---------------------------------------------------------------------------
# Codex persona compaction (shared-law de-duplication)
# ---------------------------------------------------------------------------
#
# The canonical law (the root AGENTS.md map) reaches every Codex agent context — the parent
# session AND any delegated custom agent alike — through Codex's NATIVE
# per-directory ``AGENTS.md`` discovery (`ai-harness-codex` skill §1), a
# mechanism that is entirely independent of the SessionStart/UserPromptSubmit
# hooks. Each persona body ALSO restated fragments of that same law inline — the generic
# H1 report/protocol pointer blockquotes, the Step-0 memory-bootstrap
# pointer, the `dd-handoff-emitter` artifact-emission paragraph, the
# `dd-task-manager` review-gate paragraph, and the generic `dadaia CLI`
# command list — so the law effectively loaded TWICE per Codex context: once
# via `AGENTS.md` natively, once again verbatim inside
# ``developer_instructions``. Each pattern below strips exactly one of those
# inline restatements — pure shared-law / cross-role repetition, already
# covered by `AGENTS.md` (natively) or by the named skill (loaded on demand,
# still listed in the agent's `skills:` frontmatter) — so the law loads
# exactly once. Role identity, role-specific decisions, authority and write/refusal
# boundaries are never touched by these patterns.

_CODEX_COMPACT_H1_PROTOCOL_POINTER_RE = re.compile(
    r"> This agent follows the shared workspace protocol: `AGENTS\.md` and the "
    r"projected workspace protocol\.\n\n?"
)

# "### Artifact emission" / "## Artifact emission" — the generic
# invoke-the-handoff-emitter-skill paragraph (English and the two personas
# that carry the Portuguese variant), fully covered by the
# `dd-handoff-emitter` skill's own Step 4.
_CODEX_COMPACT_ARTIFACT_EMISSION_RE = re.compile(
    r"(?:---\n\n)?###? Artifact emission\n\n"
    r"(?:After finalizing any HTML report under `\.dadaia/reports/`, invoke the\n"
    r"`dd-handoff-emitter` skill to emit handoff JSON under `\.dadaia/handoff/<context>/`\.|"
    r"Após finalizar qualquer report HTML em `\.dadaia/reports/`, invocar a skill "
    r"`dd-handoff-emitter`\npara emitir o handoff JSON em `\.dadaia/handoff/<context>/`\.)"
    r"\n\n?"
)


# "## Implementation review gate" — restates the `dd-task-manager`
# skill's "Implementation complete is not DONE" review-gate paragraph
# near-verbatim in each implementer persona that carries the skill.
_CODEX_COMPACT_REVIEW_GATE_SECTION_RE = re.compile(
    r"---\n## Implementation review gate\n\nYour completed[\s\S]*?before approval\.\n\n?"
)

# "## dadaia CLI" (never "## dadaia CLI reference", which carries the
# distinct D-1 shell-less routing content for `dd-product-engineer` and is
# never matched here) — the generic command-reference block duplicated from
# the `dadaia-cli` skill. Matched up to the next top-level heading (or EOF)
# so a persona that appends unrelated content after this heading (e.g.
# `project-auditor`'s trailing scope rule) keeps that content intact.
_CODEX_COMPACT_CLI_SECTION_RE = re.compile(r"(\n---\n)?## dadaia CLI\n.*?(?=\n## |\Z)", re.DOTALL)

# Applied in this fixed order; each pattern targets a disjoint region so
# order has no observable effect on the result, but a stable order keeps the
# diff of any future addition minimal and reviewable.
_CODEX_COMPACT_PATTERNS: tuple[re.Pattern[str], ...] = (
    _CODEX_COMPACT_H1_PROTOCOL_POINTER_RE,
    _CODEX_COMPACT_ARTIFACT_EMISSION_RE,
    _CODEX_COMPACT_REVIEW_GATE_SECTION_RE,
    _CODEX_COMPACT_CLI_SECTION_RE,
)


def _compact_codex_developer_instructions(body: str) -> str:
    """Strip shared-law / cross-role boilerplate from a Codex persona body.

    *body* is the persona body, frontmatter already stripped. Every pattern in :data:`_CODEX_COMPACT_PATTERNS`
    targets content that restates law or protocol Codex already delivers
    elsewhere in the effective context — never role identity, role-specific
    decisions, authority, or write/refusal boundaries, which ship untouched.

    Deterministic and side-effect-free: same input always yields the same
    output, independent of agent identity or call order.
    """
    result = body
    for pattern in _CODEX_COMPACT_PATTERNS:
        result = pattern.sub("", result)
    return result


# ---------------------------------------------------------------------------
# Free functions
# ---------------------------------------------------------------------------


def _render_codex_agent_toml(
    name: str,
    model: str,
    developer_instructions: str,
    *,
    reasoning_effort: str,
    description: str | None = None,
) -> str:
    """Serialize an agent as a TOML file for the Codex runtime.

    Emits Codex custom-agent fields:
    - ``name`` — basic string
    - ``description`` — basic string when available
    - ``model`` — basic string
    - ``sandbox_mode`` — always ``workspace-write``
    - ``model_reasoning_effort`` — *reasoning_effort*, as named by
      ``install_helpers.resolve_codex_agent_model`` (the one effort authority)
    - ``developer_instructions`` — triple-quoted multiline basic string

    The function avoids external TOML serialiser dependencies; it builds the
    content manually and is safe for all printable Unicode in instructions text.

    In a TOML triple-quoted basic string, backslashes are escape characters.
    All literal backslashes in the body must be doubled (``\\``), and any
    embedded triple-double-quote sequences must be escaped character-by-character
    to prevent premature string termination.

    *developer_instructions* is compacted before serialization:
    :func:`_compact_codex_developer_instructions` strips inline shared-law /
    cross-role boilerplate that Codex already delivers via native ``AGENTS.md``
    discovery or a named skill — see that function's docstring for the full
    rationale. Role identity, role-specific decisions, authority and
    write/refusal boundaries pass through unchanged.
    """
    developer_instructions = _compact_codex_developer_instructions(developer_instructions)
    # Step 1: escape backslashes first (must precede triple-quote escaping).
    escaped = developer_instructions.replace("\\", "\\\\")
    # Step 2: escape any embedded triple-double-quote sequences.
    escaped = escaped.replace('"""', '\\"\\"\\"')
    lines: list[str] = [
        f"name = {_toml_escape(name)}\n",
    ]
    if description:
        lines.append(f"description = {_toml_escape(description)}\n")
    lines.extend(
        [
            f"model = {_toml_escape(model)}\n",
            'sandbox_mode = "workspace-write"\n',
            f"model_reasoning_effort = {_toml_escape(reasoning_effort)}\n",
            f'developer_instructions = """\n{escaped}\n"""\n',
        ]
    )
    return "".join(lines)


def _render_codex_command_policy_rules() -> str:
    """Return a Codex-native Starlark command policy.

    This is intentionally narrow. The larger dadaia behavioral protocols remain
    Markdown guidance in AGENTS.md, skills, agents, and workflows; only command
    approval/denial belongs in ``.codex/rules/*.rules``.
    """
    return render_registry_tables("""# Generated by "dadaia harness add codex".

prefix_rule(
    pattern = [["ls", "cat"]],
    decision = "allow",
    justification = "Argv-closed readers only; sed, rg, find and git can write or exec, so they prompt.",
    match = ["ls -la", "cat AGENTS.md"],
    not_match = ["sed -n 1,80p AGENTS.md", "rg --pre ./x.sh pat ."],
)

prefix_rule(
    pattern = ["git", "push"],
    decision = "prompt",
    justification = "Publishing branches requires explicit operator approval after review gates.",
    match = ["git push origin feature/x"],
)

# prefix_rule matches the argv prefix LITERALLY (no PATH lookup, no basename
# normalization). The workspace mandates the venv-absolute invocation
# `.dadaia/.venv/bin/dadaia ...` (bare `dadaia` is intentionally off-PATH), so a
# pattern whose first token is `dadaia` would never fire in a compliant session.
# The ordinary install inherits the host's execution and approval policy. Only
# `--force` needs a dadaia prompt, in BOTH the documented venv-relative argv0
# form and the bare-name fallback.
prefix_rule(
    pattern = [".dadaia/.venv/bin/dadaia", "public", "install", "--force"],
    decision = "prompt",
    justification = "Forcing public install overwrites generated runtime projections.",
    match = [".dadaia/.venv/bin/dadaia public install --force"],
    not_match = [".dadaia/.venv/bin/dadaia public install"],
)

prefix_rule(
    pattern = ["dadaia", "public", "install", "--force"],
    decision = "prompt",
    justification = "Forcing public install overwrites generated runtime projections (bare-name fallback).",
    match = ["dadaia public install --force"],
    not_match = ["dadaia public install"],
)

prefix_rule(
    pattern = [".dadaia/.venv/bin/dadaia", "context", "dead"],
    decision = "prompt",
    justification = "Making a context dead syncs and removes a repository from disk.",
    match = [".dadaia/.venv/bin/dadaia context dead dadaia-workspace"],
    not_match = [".dadaia/.venv/bin/dadaia context show --json"],
)

prefix_rule(
    pattern = ["dadaia", "context", "dead"],
    decision = "prompt",
    justification = "Making a context dead syncs and removes a repository from disk (bare-name fallback).",
    match = ["dadaia context dead dadaia-workspace"],
)

prefix_rule(
    pattern = [["rm", "mv", "cp", "chmod", "chown", "sudo", "docker", "systemctl"]],
    decision = "prompt",
    justification = "Potentially destructive or host-affecting commands require review.",
    match = ["rm -rf tmp", "mv a b", "cp a b", "chmod 600 file", "sudo systemctl status app"],
)
""")


def _render_agents_config_file_blocks(agents_dir: Path) -> str:
    """Generate ``[agents."<name>"] config_file = ...`` TOML blocks.

    Replaces the inline agent block rendering.  For each canonical agent
    (determined by the ``.md`` file listing) a two-line TOML block is emitted:

    .. code-block:: toml

        [agents."<name>"]
        config_file = "agents/<name>.toml"

    Agents whose ``.md`` cannot be parsed (missing ``name``) are skipped.
    """
    if not agents_dir.exists():
        return ""
    blocks: list[str] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            fm = parse(md_file.read_text(encoding="utf-8"))
            name = str(fm.data.get("name", "")) if isinstance(fm, Frontmatter) else ""
            if not name:
                continue
            key_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
            blocks.append(f'[agents."{key_escaped}"]\n')
            blocks.append(f'config_file = "agents/{name}.toml"\n')
        except (OSError, ValueError):
            continue
    return "".join(blocks)
