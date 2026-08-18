"""Codex frontmatter-parsing and TOML/rules rendering free functions.

These functions are extracted from ``public_assets.py`` to keep that module under
600 lines.  All names remain importable from
``dadaia_workspace.infrastructure.public_assets`` via its re-export block.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.model_registry import (
    codex_effort_for_tier,
    codex_tier_views,
    registry_by_claude_id,
)
from dadaia_workspace.infrastructure.public_assets_common import _toml_escape

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Parallel workflow detection
_FRONTMATTER_PARALLEL_GROUP_RE = re.compile(r"^\s*parallel_group:\s*\S", re.MULTILINE)

_CODEX_READ_ONLY_AGENTS = frozenset(
    {
        "code-reviewer",
        "project-auditor",
        "qa-engineer",
        "security-reviewer",
        "software-architect",
    }
)
# Fallback reasoning effort when an agent's ``model:`` is unknown to the registry
# (defensive only — every canonical agent's model id is registry-backed).
_CODEX_DEFAULT_EFFORT = "medium"
# Every name/prefix here gates which backtick-quoted skill references
# ``dcx7_codex_skill_refs`` (D-CX-7) even bothers checking for existence, resolved
# against BOTH ``.agents/skills/`` and ``.codex/skills/`` (codex_doctor.py). Each entry
# must be either (a) an exact name or leading-hyphen prefix of a real
# ``public/skills/`` SOURCE skill, or (b) a documented runtime-asset exception in
# ``_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS`` below — a name that resolves to a
# Codex-only adapter projected from ``public/runtime/codex/<name>/`` (installed under
# ``.codex/skills/``, never ``public/skills/``). A name that is neither is a phantom
# prefix: it gates nothing real and would let D-CX-7 silently stop protecting the
# family it was meant to cover (A22.6; a test derives this whole tuple from the
# on-disk inventory — ``tests/contract/test_codex_skill_ref_prefixes.py``).
_CODEX_SKILL_REF_PREFIXES = (
    "ai-harness-",
    "dd-",
    "dev-server-registry",
    "harness-primitives",
    "memory-ctx",
    "project-orchestration",
)

# (A22.6) ``memory-ctx`` is a Codex-only runtime adapter — the packaged source lives
# at ``public/runtime/codex/memory-ctx/SKILL.md`` and is projected to
# ``.codex/skills/memory-ctx/SKILL.md`` by ``dcx6_codex_runtime_adapters``, never to
# ``public/skills/``. It is a real, resolvable asset, not a phantom: it just lives on
# the runtime-adapter surface instead of the skills surface D-CX-7 checks first.
_CODEX_SKILL_REF_RUNTIME_ASSET_EXCEPTIONS: frozenset[str] = frozenset({"memory-ctx"})

# Whitelist of agent frontmatter fields that may be emitted to codex config.toml.
_TOML_SAFE_AGENT_FIELDS: frozenset[str] = frozenset({"name", "description", "model", "tools"})

# Matches a YAML list item under `tools:` (e.g. "  - Read")
_AGENT_FM_TOOLS_ITEM_RE = re.compile(r"^  - (.+)$", re.MULTILINE)
# Matches a simple `key: value` line in frontmatter (single-line value)
_AGENT_FM_SIMPLE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): (.+)$", re.MULTILINE)
# Matches a folded/literal scalar intro: `key: >` or `key: |`
_AGENT_FM_BLOCK_SCALAR_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*): [>|]$", re.MULTILINE)

# ---------------------------------------------------------------------------
# FR22 / A22.1 — Codex persona compaction (shared-law de-duplication)
# ---------------------------------------------------------------------------
#
# The canonical law (DADAIA.md) reaches every Codex agent context — the parent
# session AND any delegated custom agent alike — through Codex's NATIVE
# per-directory ``AGENTS.md`` discovery (`ai-harness-codex` skill §1), a
# mechanism that is entirely independent of the SessionStart/UserPromptSubmit
# hooks (live-verified, codex-cli 0.147.0, T-043-33: a parent `codex exec`
# session AND a delegated `agent_type="software-engineer"` subagent both
# quoted the literal opening words of the projected root AGENTS.md from their
# own context, unprompted by any tool call). Before this compaction, every
# persona body ALSO restated fragments of that same law inline — the generic
# H1 report/protocol pointer blockquotes, the Step-0 memory-bootstrap
# pointer, the `dadaia-handoff-emitter` artifact-emission paragraph, the
# `dadaia-task-manager` review-gate paragraph, and the generic `dadaia CLI`
# command list — so the law effectively loaded TWICE per Codex context: once
# via `AGENTS.md` natively, once again verbatim inside
# ``developer_instructions``. Each pattern below strips exactly one of those
# inline restatements — pure shared-law / cross-role repetition, already
# covered by `AGENTS.md` (natively) or by the named skill (loaded on demand,
# still listed in the agent's `skills:` frontmatter) — so the law loads
# exactly once (A22.2). Role identity, role-specific decisions, authority and
# write/refusal boundaries are never touched by these patterns.

# The two generic pointer lines directly under the H1 title. Only an EXACT
# match is stripped, so a persona (e.g. project-manager) that weaves
# role-specific prose into the same blockquote keeps its own sentence.
_CODEX_COMPACT_H1_REPORTS_POINTER_RE = re.compile(
    r"> Reports follow the `DADAIA\.md` \(the workspace law\) §4 \(handoff-first\)[^\n]*\n\n?"
)
_CODEX_COMPACT_H1_PROTOCOL_POINTER_RE = re.compile(
    r"> This agent follows the shared workspace protocol: `AGENTS\.md` and the "
    r"projected workspace protocol\.\n\n?"
)

# "## Step 0 — Memory bootstrap" — a byte-identical (modulo one trailing
# clause) heading + one-line pointer to the `dadaia-step0-memory-bootstrap`
# skill, repeated in every implementer/reviewer persona. The skill itself
# (already in the agent's `skills:` list) carries the full protocol.
_CODEX_COMPACT_STEP0_SECTION_RE = re.compile(
    r"## Step 0 — Memory bootstrap \(mandatory, before any work\)\n\n"
    r"Execute the `dadaia-step0-memory-bootstrap` skill before any[^\n]*\.\n\n"
    r"---\n\n"
)

# "### Artifact emission" / "## Artifact emission" — the generic
# invoke-the-handoff-emitter-skill paragraph (English and the two personas
# that carry the Portuguese variant), fully covered by the
# `dadaia-handoff-emitter` skill's own Step 4.
_CODEX_COMPACT_ARTIFACT_EMISSION_RE = re.compile(
    r"(?:---\n\n)?###? Artifact emission\n\n"
    r"(?:After finalizing any HTML report under `\.dadaia/reports/`, invoke the\n"
    r"`dadaia-handoff-emitter` skill to emit handoff JSON under `\.dadaia/handoff/<context>/`\.|"
    r"Após finalizar qualquer report HTML em `\.dadaia/reports/`, invocar a skill "
    r"`dadaia-handoff-emitter`\npara emitir o handoff JSON em `\.dadaia/handoff/<context>/`\.)"
    r"\n\n?"
)

# The trailing "> Report/handoff emission follows the DADAIA.md ... §4 ..."
# blockquote — byte-identical (modulo one qa-engineer addendum clause) in
# every persona, restating the same DADAIA.md §4 handoff-first policy already
# named earlier in the same "## Report" section.
_CODEX_COMPACT_HANDOFF_POINTER_RE = re.compile(
    r"\n?> Report/handoff emission follows the `DADAIA\.md`[^\n]*\n\n?"
)

# "## Implementation review gate" — restates the `dadaia-task-manager`
# skill's "Implementation complete is not DONE" review-gate paragraph
# near-verbatim in each implementer persona that carries the skill.
_CODEX_COMPACT_REVIEW_GATE_SECTION_RE = re.compile(
    r"---\n## Implementation review gate\n\nYour completed[\s\S]*?before approval\.\n\n?"
)

# "## dadaia CLI" (never "## dadaia CLI reference", which carries the
# distinct D-1 shell-less routing content for `product-engineer` and is
# never matched here) — the generic command-reference block duplicated from
# the `dadaia-cli` skill. Matched up to the next top-level heading (or EOF)
# so a persona that appends unrelated content after this heading (e.g.
# `project-auditor`'s trailing scope rule) keeps that content intact.
_CODEX_COMPACT_CLI_SECTION_RE = re.compile(r"(\n---\n)?## dadaia CLI\n.*?(?=\n## |\Z)", re.DOTALL)

# Applied in this fixed order; each pattern targets a disjoint region so
# order has no observable effect on the result, but a stable order keeps the
# diff of any future addition minimal and reviewable.
_CODEX_COMPACT_PATTERNS: tuple[re.Pattern[str], ...] = (
    _CODEX_COMPACT_H1_REPORTS_POINTER_RE,
    _CODEX_COMPACT_H1_PROTOCOL_POINTER_RE,
    _CODEX_COMPACT_STEP0_SECTION_RE,
    _CODEX_COMPACT_ARTIFACT_EMISSION_RE,
    _CODEX_COMPACT_HANDOFF_POINTER_RE,
    _CODEX_COMPACT_REVIEW_GATE_SECTION_RE,
    _CODEX_COMPACT_CLI_SECTION_RE,
)


def _compact_codex_developer_instructions(body: str) -> str:
    """Strip shared-law / cross-role boilerplate from a Codex persona body (A22.1).

    *body* is the already Codex-transformed persona body (post
    :func:`~dadaia_workspace.infrastructure.runtime_transforms.codex.transform_for_codex`,
    frontmatter already stripped). Every pattern in :data:`_CODEX_COMPACT_PATTERNS`
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


def _render_agents_into_codex_config(agents_dir: Path) -> str:
    """Scan *agents_dir* for ``.md`` agent files and render TOML ``[agents.*]`` blocks.

    For each ``.md`` file (sorted for determinism):
    1. Parse YAML frontmatter via ``_parse_agent_frontmatter()``.
    2. If the result is non-empty (i.e., ``name`` key present), render via
       ``_render_agent_toml_block()``.
    3. Agents whose frontmatter cannot be parsed or are missing ``name`` are
       silently skipped (defensive — never breaks install).

    Returns the concatenated block string (may be empty string when no agents
    are found).
    """
    if not agents_dir.exists():
        return ""
    blocks: list[str] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_agent_frontmatter(text)
            if not fm:
                continue
            name = str(fm.get("name", ""))
            if not name:
                continue
            blocks.append(_render_agent_toml_block(name, fm))
        except (OSError, ValueError):
            continue
    return "\n".join(blocks) + ("\n" if blocks else "")


def _codex_reasoning_effort_for_model(claude_model: str | None) -> str:
    """Resolve the Codex ``model_reasoning_effort`` from an agent's ``model:``.

    The effort is derived from the registry tier view (the single source of
    truth) rather than a hand-maintained per-agent table: the frontmatter
    ``model:`` (a Claude id) resolves to its registry tier, which the
    per-runtime view maps to a Codex reasoning effort (``deep`` -> ``high``,
    everything else -> ``medium``). This call also exercises
    :func:`codex_tier_views`, so a tier collapse (two distinct tiers resolving
    to one (model, effort) pair) fails loudly at projection time.

    Returns ``_CODEX_DEFAULT_EFFORT`` when *claude_model* is ``None`` or not in
    the registry (defensive — never breaks install).
    """
    # Invariant guard: raises loudly if the live registry collapses two tiers.
    codex_tier_views()
    if not claude_model:
        return _CODEX_DEFAULT_EFFORT
    entry = registry_by_claude_id().get(claude_model)
    if entry is None:
        return _CODEX_DEFAULT_EFFORT
    return codex_effort_for_tier(entry.tier)


def _render_codex_agent_toml(
    name: str,
    model: str,
    developer_instructions: str,
    description: str | None = None,
    claude_model: str | None = None,
    reasoning_effort: str | None = None,
) -> str:
    """Serialize an agent as a TOML file for the Codex runtime.

    Emits Codex custom-agent fields:
    - ``name`` — basic string
    - ``description`` — basic string when available
    - ``model`` — basic string
    - ``sandbox_mode`` — conservative role boundary
    - ``model_reasoning_effort`` — explicit reasoning profile: *reasoning_effort*
      when supplied (the D-3 clamp of the RESOLVED agent-model-policy effort,
      v0.1.65 FR5); otherwise derived from the registry tier of *claude_model*
      via the per-runtime tier view (legacy path — staged bodies without a
      resolved policy)
    - ``developer_instructions`` — triple-quoted multiline basic string

    The function avoids external TOML serialiser dependencies; it builds the
    content manually and is safe for all printable Unicode in instructions text.

    In a TOML triple-quoted basic string, backslashes are escape characters.
    All literal backslashes in the body must be doubled (``\\``), and any
    embedded triple-double-quote sequences must be escaped character-by-character
    to prevent premature string termination.

    *developer_instructions* is compacted (A22.1, FR22b) before serialization:
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
    sandbox_mode = "read-only" if name in _CODEX_READ_ONLY_AGENTS else "workspace-write"
    if reasoning_effort is None:
        reasoning_effort = _codex_reasoning_effort_for_model(claude_model)
    lines.extend(
        [
            f"model = {_toml_escape(model)}\n",
            f"sandbox_mode = {_toml_escape(sandbox_mode)}\n",
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
    return """# Generated by "dadaia public install --target codex".

prefix_rule(
    pattern = [["rg", "ls", "find", "cat", "sed"]],
    decision = "allow",
    justification = "Read-only local inspection commands are safe in the dadaia workspace.",
    match = ["rg Codex", "ls -la", "find specs -maxdepth 2 -type f", "cat AGENTS.md", "sed -n 1,80p AGENTS.md"],
)

prefix_rule(
    pattern = ["git", ["status", "diff", "log", "show"]],
    decision = "allow",
    justification = "Local git inspection is safe and needed for review.",
    match = ["git status --short", "git diff", "git log --oneline", "git show HEAD"],
    not_match = ["git push", "git commit"],
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
# We therefore gate BOTH the venv-relative argv0 form actually used in this
# workspace's docs AND the bare name (for any non-compliant PATH invocation), and
# prove the real form in `match=`.
prefix_rule(
    pattern = [".dadaia/.venv/bin/dadaia", "public", "install"],
    decision = "prompt",
    justification = "Public install rewrites generated runtime projections.",
    match = [".dadaia/.venv/bin/dadaia public install --target codex", ".dadaia/.venv/bin/dadaia public install --target all"],
    not_match = [".dadaia/.venv/bin/dadaia public doctor"],
)

prefix_rule(
    pattern = ["dadaia", "public", "install"],
    decision = "prompt",
    justification = "Public install rewrites generated runtime projections (bare-name fallback).",
    match = ["dadaia public install --target codex", "dadaia public install --target all"],
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
"""


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
            text = md_file.read_text(encoding="utf-8")
            fm = _parse_agent_frontmatter(text)
            if not fm:
                continue
            name = str(fm.get("name", ""))
            if not name:
                continue
            key_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
            blocks.append(f'[agents."{key_escaped}"]\n')
            blocks.append(f'config_file = "agents/{name}.toml"\n')
        except (OSError, ValueError):
            continue
    return "".join(blocks)


def _render_agent_toml_block(name: str, fm: dict[str, object]) -> str:
    """Render a ``[agents."<name>"]`` TOML table block from parsed frontmatter *fm*.

    Keys are always quoted for safety (required for hyphenated names like
    ``software-engineer``). Missing or None fields are omitted. The ``tools``
    field, if present, is emitted as a TOML array of basic strings.

    Names containing ``]`` or newline characters are rejected (cannot appear
    safely inside a TOML table header, even with quoting). Double-quotes and
    backslashes are escaped with a leading backslash so the header is valid
    TOML (e.g. a name like ``a"b`` becomes ``[agents."a\\"b"]``).
    """
    if "]" in name:
        raise ValueError(f"Agent name contains invalid character ']': {name!r}")
    if "\n" in name:
        raise ValueError(f"Agent name contains newline character: {name!r}")
    # Escape backslash first (must precede quote escape to avoid double-escaping)
    key_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    lines: list[str] = [f'[agents."{key_escaped}"]\n']
    for field in ("name", "description", "model"):
        val = fm.get(field)
        if val is None:
            continue
        lines.append(f"{field} = {_toml_escape(val)}\n")
    tools_val = fm.get("tools")
    if tools_val is not None and isinstance(tools_val, list):
        items = ", ".join(_toml_escape(t) for t in tools_val)
        lines.append(f"tools = [{items}]\n")
    return "".join(lines)


def _parse_agent_frontmatter(text: str) -> dict[str, object]:
    """Parse YAML frontmatter from an agent .md file using stdlib regex only.

    Extracts the block between the first pair of ``---`` fences. Supports:
    - Simple ``key: value`` scalar fields (string values).
    - Folded scalar ``key: >`` — continuation lines are joined with a space.
    - YAML list under ``tools:`` — items prefixed with ``  - `` (two-space indent).

    Unknown fields (outside ``_TOML_SAFE_AGENT_FIELDS``) are silently dropped.
    Returns an empty dict if ``name`` is missing or frontmatter is absent.
    """
    if not text.startswith("---\n"):
        return {}
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return {}
    frontmatter = text[4 : end_idx + 1]

    result: dict[str, object] = {}
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect block scalar (folded `>` or literal `|`)
        block_m = _AGENT_FM_BLOCK_SCALAR_RE.match(line)
        if block_m:
            key = block_m.group(1)
            # Collect continuation lines (indented)
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                body_lines.append(lines[i].strip())
                i += 1
            # Join non-empty continuation lines with a space (folded scalar semantics)
            value = " ".join(part for part in body_lines if part)
            if key in _TOML_SAFE_AGENT_FIELDS:
                result[key] = value
            continue

        # Detect tools list  (`tools:\n  - item\n  - item`)
        if line == "tools:":
            items: list[str] = []
            i += 1
            while i < len(lines) and _AGENT_FM_TOOLS_ITEM_RE.match(lines[i]):
                m = _AGENT_FM_TOOLS_ITEM_RE.match(lines[i])
                if m:
                    items.append(m.group(1).strip())
                i += 1
            if "tools" in _TOML_SAFE_AGENT_FIELDS:
                result["tools"] = items
            continue

        # Simple scalar
        simple_m = _AGENT_FM_SIMPLE_RE.match(line)
        if simple_m:
            key = simple_m.group(1)
            value_str = simple_m.group(2).strip()
            if key in _TOML_SAFE_AGENT_FIELDS:
                result[key] = value_str
        i += 1

    # Require `name` — without it, the block cannot be rendered
    if "name" not in result:
        return {}
    return result


def _parse_write_allowlist(text: str) -> list[str]:
    """Extract ``paths.write_allowlist`` globs from agent .md frontmatter (stdlib only).

    Used to pre-compile ``.dadaia/agentic/agents.index.json`` (T-016-00) so the SDD
    gate's RULE D performs an O(1) JSON lookup instead of an inline YAML parse on
    every PreToolUse. Returns ``[]`` when the agent declares no write_allowlist.
    """
    if not text.startswith("---\n"):
        return []
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return []

    in_paths = False
    in_wl = False
    items: list[str] = []
    for line in text[4 : end_idx + 1].splitlines():
        if not line.strip():
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_paths = stripped == "paths:"
            in_wl = False
            continue
        if not in_paths:
            continue
        if in_wl and stripped.startswith("- "):
            items.append(stripped[2:].strip())
            continue
        # A sub-key under `paths:` (write_allowlist:, read_allowlist:, …).
        in_wl = stripped == "write_allowlist:"
    return items


def _parse_skills_from_frontmatter(text: str) -> list[str]:
    """Extract the ``skills:`` list from agent YAML frontmatter.

    Locates the ``skills:`` key inside the opening ``---`` block and collects
    indented ``  - <name>`` list items, stopping at the next top-level key or
    end of the frontmatter block.  Returns an empty list when frontmatter is
    absent or contains no ``skills:`` key.
    """
    if not text.startswith("---\n"):
        return []
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return []
    frontmatter = text[4 : end_idx + 1]

    skills: list[str] = []
    in_skills = False
    for line in frontmatter.splitlines():
        if line.rstrip() == "skills:":
            in_skills = True
            continue
        if in_skills:
            stripped = line.strip()
            if stripped.startswith("- "):
                skills.append(stripped[2:].strip())
            elif line and not line.startswith(" ") and not line.startswith("\t"):
                in_skills = False  # next top-level key — skills block ended
    return skills
