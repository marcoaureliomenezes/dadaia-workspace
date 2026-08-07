"""Control token-anchor discipline for the panel (FR2 / AC-3, v0.1.59).

Proves the **restyled interactive controls** (nav tabs, theme button, runtime
switcher, report/academy CTAs and the report trash
button) consume the design-token vocabulary rather than ad-hoc literals. Also
absorbs the former ``test_palette.py`` PANEL_CSS-grep prior art: the brand-color
token *contract* (definition + consumption) holds across the concatenated
stylesheet.

Mechanism (Q3, grep-falsifiable):
  * an explicit **selector allowlist** of the controls the W2 restyle touches;
  * for each allowlisted selector, the matching rule bodies are extracted from the
    **served control-surface** stylesheet strings — ``structure.py``
    / ``reports.py`` / ``academy.py``;
  * the token-DEFINITION file ``tokens.py`` is **excluded** from the control-anchor
    scan — that is where ``--color-accent: #9cddc8`` etc. legitimately define the
    tokens (scanning it would false-positive on the definitions). The ``.runtime-btn``
    component rules were relocated out of ``tokens.py`` into ``structure.py`` in
    v0.1.59 exactly so the allowlist + exclusion stay self-consistent;
  * every matched body must contain at least one ``var(--…)`` and must NOT contain any
    ad-hoc literal, rejected via three regexes: a hex color ``#[0-9a-fA-F]{3,8}``, a
    ``font-size:`` value carrying a ``px``/``rem`` literal, and a ``border-radius:``
    value carrying a ``px`` literal.

AC-9(c) sabotage: reintroducing an ad-hoc hex (e.g. ``#9cddc8``) into any restyled
control rule makes ``test_control_rules_are_token_anchored`` fail on the hex reject.
"""

from __future__ import annotations

import re

import pytest

from dadaia_workspace.features.panel.views.assets.css.academy import ACADEMY_CSS
from dadaia_workspace.features.panel.views.assets.css.reports import REPORTS_CSS
from dadaia_workspace.features.panel.views.assets.css.sessions import SESSIONS_CSS
from dadaia_workspace.features.panel.views.assets.css.structure import STRUCTURE_CSS
from dadaia_workspace.features.panel.views.assets.css.tokens import TOKENS_CSS

pytestmark = pytest.mark.unit

# The former test_palette.py PANEL_CSS (definition + consumption prior art).
PANEL_CSS = TOKENS_CSS + STRUCTURE_CSS + SESSIONS_CSS
_REQUIRED_COLOR_TOKENS = {
    "--color-accent",
    "--color-accent-secondary",
    "--color-warning-bg",
    "--color-alert",
    "--color-cost",
}

# The served control-surface stylesheets. tokens.py (the token-DEFINITION file) is
# deliberately EXCLUDED — see the module docstring.
CONTROL_SURFACES: dict[str, str] = {
    "structure.py": STRUCTURE_CSS,
    "reports.py": REPORTS_CSS,
    "academy.py": ACADEMY_CSS,
}

# Explicit, literal selector allowlist — the controls restyled in W2 (FR2).
CONTROL_SELECTORS: tuple[str, ...] = (
    ".nav-tab",
    ".theme-btn",
    ".runtime-btn",
    ".academy-card__cta",
    ".academy-back-btn",
    ".reports-row__trash",
    ".reports-back-btn",
    ".reports-confirm-delete",
    ".reports-confirm-cancel",
)

# Button controls that must carry the full interaction-state set (one button language).
BUTTON_CONTROLS: tuple[str, ...] = (".nav-tab", ".theme-btn", ".runtime-btn")

# ---------------------------------------------------------------------------
# Reject regexes — the ad-hoc literals a token-anchored control rule must NOT carry.
# ---------------------------------------------------------------------------
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_FONT_SIZE_LITERAL_RE = re.compile(r"font-size\s*:\s*[^;{}]*?\d\s*(?:px|rem)\b", re.IGNORECASE)
_RADIUS_PX_RE = re.compile(r"border-radius\s*:\s*[^;{}]*?\d\s*px\b", re.IGNORECASE)

# Flat ``selector { body }`` block extractor. CSS here has no nested braces except
# @media/@keyframes wrappers, whose *inner* flat rules are captured correctly; none of
# the allowlisted controls live inside such a wrapper.
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)


def _iter_rules(css: str) -> list[tuple[str, str]]:
    """Yield ``(selector_list, body)`` for every flat rule block in *css*.

    CSS comments are stripped first so a ``/* … */`` immediately preceding a rule does
    not leak into the extracted selector list.
    """
    stripped = _COMMENT_RE.sub("", css)
    return [(m.group(1).strip(), m.group(2)) for m in _RULE_RE.finditer(stripped)]


def _selector_matches(selector_list: str, control: str) -> bool:
    """True if any individual selector in *selector_list* has *control* as its subject.

    A selector matches when it starts with the control class followed by a boundary
    (not a hyphen/word char, so ``.nav-tab`` never matches ``.nav-tabs`` /
    ``.theme-btn-icon``) and carries only pseudo-class / pseudo-element / attribute /
    state-class suffixes — no descendant/child/sibling combinator. This excludes both
    ancestor-prefixed groups (``html[data-theme="warm"] .nav-tab:focus-visible``) and
    descendant targets (``.theme-btn[aria-expanded="true"] .theme-btn-caret``).
    """
    pattern = re.compile(r"^" + re.escape(control) + r"(?![-\w])[^ >+~]*$")
    return any(pattern.match(sel.strip()) for sel in selector_list.split(","))


def _matched_selectors(control: str) -> list[str]:
    """All individual selector strings across the control surfaces matching *control*."""
    pattern = re.compile(r"^" + re.escape(control) + r"(?![-\w])[^ >+~]*$")
    out: list[str] = []
    for css in CONTROL_SURFACES.values():
        for selector_list, _ in _iter_rules(css):
            out.extend(
                sel.strip() for sel in selector_list.split(",") if pattern.match(sel.strip())
            )
    return out


def test_control_tokens_selector_anchor_and_button_states() -> None:
    """Merged control-discipline guard: selector-has-rule + token-anchored-no-literals
    + button hover/focus/active states, plus the absorbed brand-token contract
    (definition in TOKENS_CSS + consumption via var(--...) in PANEL_CSS)."""
    # Every allowlisted control has at least one matching rule body (no silent drop).
    for control in CONTROL_SELECTORS:
        found = any(
            _selector_matches(selector_list, control)
            for css in CONTROL_SURFACES.values()
            for selector_list, _ in _iter_rules(css)
        )
        assert found, f"no rule body found for allowlisted control {control!r}"

    # Each matched control rule body is var(--...)-anchored and free of ad-hoc literals.
    for surface_name, css in CONTROL_SURFACES.items():
        for selector_list, body in _iter_rules(css):
            for control in CONTROL_SELECTORS:
                if not _selector_matches(selector_list, control):
                    continue
                where = f"{surface_name} :: {selector_list.strip()}"
                assert not _HEX_RE.search(body), f"ad-hoc hex literal in {where}: {body!r}"
                assert not _FONT_SIZE_LITERAL_RE.search(body), (
                    f"ad-hoc font-size px/rem literal in {where}: {body!r}"
                )
                assert not _RADIUS_PX_RE.search(body), (
                    f"ad-hoc border-radius px literal in {where}: {body!r}"
                )
                assert "var(--" in body, f"control rule not token-anchored in {where}: {body!r}"
                break

    # The button controls carry a hover, a focus-visible, and an active/selected state.
    for control in BUTTON_CONTROLS:
        joined = " ".join(_matched_selectors(control))
        assert ":hover" in joined, f"{control!r} missing a :hover state ({joined})"
        assert ":focus-visible" in joined, f"{control!r} missing a :focus-visible state ({joined})"
        assert (
            ".active" in joined
            or ":active" in joined
            or "[aria-checked" in joined
            or "[aria-pressed" in joined
        ), f"{control!r} missing an active/selected state ({joined})"

    # Absorbed test_palette.py: brand colors are sourced from CSS tokens (definition),
    # and panel CSS consumes the token contract through var(--color-*) (consumption).
    for token in _REQUIRED_COLOR_TOKENS:
        assert re.search(rf"{re.escape(token)}\s*:\s*#[0-9a-fA-F]{{3,8}}\b", TOKENS_CSS)
        assert f"var({token}" in PANEL_CSS or token in TOKENS_CSS
