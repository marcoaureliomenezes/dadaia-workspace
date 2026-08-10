"""Agentic Entities tab — the abstract-entity surface, server-rendered.

Renders the packaged abstract-entity registry
(``dadaia_workspace/public/entities/registry.json`` via
``features.panel.entities``) plus the packaged core-skill tree into the
"Agentic Entities" tabpanel:

  - **Agnostic (Universal)** — Skills (``.agents/skills/``) and the AGENTS.md
    guardrail files: read natively by every supported harness, so they carry no
    harness dimension at all (no toggle).
  - **Deterministic Actions** — the abstract Deterministic Behaviors, each card
    expanding into its per-harness hook implementation.
  - **Rules** — the abstract rules, each card expanding into its per-harness
    projection.

Every card is MINIMAL by design: the collapsed face is the entity's name only;
``<details>``/``<summary>`` provides click-to-expand with zero JavaScript.

Security (OWASP A03): all data originates from the installed package itself
(registry JSON + SKILL.md frontmatter) — no operator or workspace input — and is
still passed through ``html.escape()`` before interpolation, so a hostile string
in a modified install cannot break out of the markup.

Scope (constitution §12.5): only lib-scaffolded CORE entities appear here.
Operator-created sub-agents, skills and rules are exempt from the derivation law
and are deliberately absent from this tab.
"""

from __future__ import annotations

import html
from typing import Any

from dadaia_workspace.features.panel.entities import core_skills, load_registry


def render_entities_section() -> str:
    """Return the fully server-rendered "Agentic Entities" tabpanel."""
    registry = load_registry()
    return (
        '<section id="section-entities" class="section" '
        'aria-label="Agentic entities scaffolded by dadaia-workspace" '
        'role="tabpanel" tabindex="0" aria-labelledby="tab-entities">\n'
        '      <header class="section-header">\n'
        "        <h2>Agentic Entities</h2>\n"
        "      </header>\n"
        '      <details class="section-desc">\n'
        "        <summary>About this section</summary>\n"
        "        <p>Everything dadaia-workspace scaffolds is defined here as an "
        "abstract, harness-agnostic entity first — and only then derived per "
        "harness. Sub-agents derive from <strong>Personas</strong> (see the "
        "Agents tab), hooks from <strong>Deterministic Behaviors</strong>, rule "
        "files from <strong>Abstract Rules</strong>; skills and AGENTS.md are "
        "universal — read natively by Claude Code, Codex and Kimi CLI. A core "
        "implementation without its abstract entity is forbidden. "
        "Operator-created entities are out of scope and never appear here.</p>\n"
        "      </details>\n"
        f"{_render_universal(registry)}"
        f"{_render_behaviors(registry)}"
        f"{_render_rules(registry)}"
        "    </section>"
    )


def render_personas_section() -> str:
    """The leading Personas sub-section of the Agents tab.

    Persona = the abstract entity every scaffolded core sub-agent derives from
    (constitution §12.5). Same minimal ``<details>`` cards as the Agentic
    Entities tab; the roster below it shows the derived, per-harness sub-agents.
    """
    registry = load_registry()
    cards = "".join(
        _card(
            persona["id"],
            "plugin stub" if persona.get("plugin") else "persona",
            f"<p>{html.escape(persona['mandate'])}</p>",
        )
        for persona in registry["personas"]
    )
    return (
        '<div class="ent-topic" id="ap-personas">\n'
        "        <h3>Personas <span class='ent-topic-note'>the abstract entities "
        "— every scaffolded sub-agent below derives from one of these</span></h3>\n"
        f'        <div class="ent-grid">{cards}</div>\n'
        "      </div>"
    )


def _card(title: str, badge: str, body_html: str) -> str:
    """One minimal, click-to-expand entity card (collapsed face = name + badge)."""
    return (
        '<details class="ent-card">'
        f'<summary><span class="ent-card-name">{html.escape(title)}</span>'
        f'<span class="ent-badge">{html.escape(badge)}</span></summary>'
        f'<div class="ent-card-body">{body_html}</div>'
        "</details>"
    )


def _impl_rows(implementations: dict[str, str]) -> str:
    """Per-harness implementation rows for an expanded card."""
    rows = "".join(
        f'<div class="ent-impl-row"><span class="ent-impl-harness">{html.escape(harness)}</span>'
        f"<code>{html.escape(impl)}</code></div>"
        for harness, impl in implementations.items()
    )
    return f'<div class="ent-impl">{rows}</div>'


def _render_universal(registry: dict[str, Any]) -> str:
    universal = registry["universal"]
    skills_root = str(universal["skills_root"])
    skill_cards = "".join(
        _card(
            name,
            "skill",
            f"<p>{html.escape(description)}</p>"
            f"<code class='ent-path'>{html.escape(skills_root + name + '/')}</code>",
        )
        for name, description in core_skills()
    )
    agents_md_cards = "".join(
        _card(
            str(entry).split(" ", 1)[0],
            "AGENTS.md",
            f"<p>{html.escape(str(entry))}</p>",
        )
        for entry in universal["agents_md"]
    )
    return (
        '      <div class="ent-topic">\n'
        "        <h3>Agnostic <span class='ent-topic-note'>universal — no harness "
        "dimension; Claude Code, Codex and Kimi CLI all read these natively</span></h3>\n"
        f'        <h4>Skills <code class="ent-path">{html.escape(skills_root)}</code></h4>\n'
        f'        <div class="ent-grid">{skill_cards}</div>\n'
        "        <h4>AGENTS.md</h4>\n"
        '        <div class="ent-grid">'
        f"{agents_md_cards}</div>\n"
        "      </div>\n"
    )


def _render_behaviors(registry: dict[str, Any]) -> str:
    cards = "".join(
        _card(
            behavior["id"],
            "behavior",
            f"<p>{html.escape(behavior['mandate'])}</p>" + _impl_rows(behavior["implementations"]),
        )
        for behavior in registry["behaviors"]
    )
    return (
        '      <div class="ent-topic">\n'
        "        <h3>Deterministic Actions <span class='ent-topic-note'>abstract "
        "behavior first, then the hook that enforces it per harness</span></h3>\n"
        '        <div class="ent-grid">'
        f"{cards}</div>\n"
        "      </div>\n"
    )


def _render_rules(registry: dict[str, Any]) -> str:
    cards = "".join(
        _card(
            rule["id"],
            "rule",
            f"<p>{html.escape(rule['mandate'])}</p>" + _impl_rows(rule["implementations"]),
        )
        for rule in registry["rules"]
    )
    return (
        '      <div class="ent-topic">\n'
        "        <h3>Rules <span class='ent-topic-note'>abstract rule first, then "
        "its projection per harness</span></h3>\n"
        '        <div class="ent-grid">'
        f"{cards}</div>\n"
        "      </div>\n"
    )
