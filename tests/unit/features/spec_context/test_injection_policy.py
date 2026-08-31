"""F009 (20260830-design-bug-surface-audit): the ctx-inject decision is PURE policy
(``injection_policy.decide_injection``), testable as a decision table — no stdin, no
env, no files. The hook is transport. Intent: contract; size: unit.

The table encodes the four historical bug fixes as rows:
- kimi-postcompact-omits-bound-context-bootstrap (recorded-slug fallback),
- claude-compact-reinjection-missing (session_restart re-emits AND restamps),
- ctx-inject-newest-bind-epoch-steals-other-sessions-context (self-keyed rebind),
- the compact-marker re-injection trigger.
"""

from __future__ import annotations

from dadaia_workspace.features.spec_context.injection_policy import (
    InjectionDecision,
    decide_injection,
)


def _has_specs(name: str) -> bool:
    return name in {"alpha", "beta"}


def test_prompt_fresh_session_bound_context_bootstraps_and_stamps() -> None:
    d = decide_injection(
        event="prompt",
        context="alpha",
        recorded_slug="",
        sentinel_exists=False,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("bootstrap", "alpha", "alpha")


def test_prompt_repeat_same_slug_is_silent() -> None:
    d = decide_injection(
        event="prompt",
        context="alpha",
        recorded_slug="alpha",
        sentinel_exists=True,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("none")


def test_prompt_rebind_to_other_context_reinjects() -> None:
    d = decide_injection(
        event="prompt",
        context="beta",
        recorded_slug="alpha",
        sentinel_exists=True,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("bootstrap", "beta", "beta")


def test_prompt_same_context_rebind_reinjects() -> None:
    # T-50-03: a same-context re-bind (mode/release change) MUST re-inject.
    d = decide_injection(
        event="prompt",
        context="alpha",
        recorded_slug="alpha",
        sentinel_exists=True,
        compacted=False,
        rebound=True,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("bootstrap", "alpha", "alpha")


def test_prompt_compacted_reinjects_recorded_slug_when_unresolved() -> None:
    d = decide_injection(
        event="prompt",
        context="",
        recorded_slug="alpha",
        sentinel_exists=True,
        compacted=True,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("bootstrap", "alpha", "alpha")


def test_prompt_unbound_fresh_session_gets_preflight_once() -> None:
    d = decide_injection(
        event="prompt",
        context="",
        recorded_slug="",
        sentinel_exists=False,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("preflight", "", "")
    d2 = decide_injection(
        event="prompt",
        context="",
        recorded_slug="",
        sentinel_exists=True,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d2 == InjectionDecision("none")


def test_prompt_context_without_specs_degrades_to_preflight() -> None:
    d = decide_injection(
        event="prompt",
        context="ghost",
        recorded_slug="",
        sentinel_exists=False,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("preflight", "", "")


def test_postcompact_emits_bootstrap_but_never_stamps() -> None:
    d = decide_injection(
        event="postcompact",
        context="",
        recorded_slug="alpha",
        sentinel_exists=True,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("bootstrap", "alpha", None)


def test_postcompact_unbound_emits_preflight_without_stamp() -> None:
    d = decide_injection(
        event="postcompact",
        context="",
        recorded_slug="",
        sentinel_exists=False,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("preflight", "", None)


def test_session_restart_bootstraps_and_restamps() -> None:
    # claude-compact-reinjection-missing: re-emit at the event ITSELF and restamp so
    # the next prompt stays silent (exactly-once discipline).
    d = decide_injection(
        event="session_restart",
        context="",
        recorded_slug="alpha",
        sentinel_exists=True,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("bootstrap", "alpha", "alpha")


def test_session_restart_unbound_preflights_and_stamps_empty() -> None:
    d = decide_injection(
        event="session_restart",
        context="",
        recorded_slug="",
        sentinel_exists=False,
        compacted=False,
        rebound=False,
        has_specs=_has_specs,
    )
    assert d == InjectionDecision("preflight", "", "")
