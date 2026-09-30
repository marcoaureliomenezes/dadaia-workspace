"""F009 (20260830-design-bug-surface-audit): the ctx-inject decision is PURE policy
(``injection_policy.decide_injection``) — a decision table, no stdin, env or files.

Intent: CONTRACT — rows encode kimi-postcompact-omits-bound-context-bootstrap (recorded-slug
fallback), claude-compact-reinjection-missing (session_restart re-emits AND restamps),
ctx-inject-newest-bind-epoch-steals-other-sessions-context (self-keyed rebind), the
compact-marker trigger, sa-bind-has-two-stores#S7, bind-lost-silently-after-five-idle-minutes and
AC1.2 ctx-inject-on-cursor-copilot (session_start is a new session in every harness).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.spec_context.injection_policy import (
    InjectionDecision,
    decide_injection,
)

_NONE = InjectionDecision("none")


# fmt: off
@pytest.mark.parametrize(("event", "context", "recorded", "sentinel", "compacted", "rebound", "expected"), [
    pytest.param("prompt", "alpha", "", False, False, False, InjectionDecision("bootstrap", "alpha", "alpha"), id="fresh-bound-bootstraps-and-stamps"),
    pytest.param("prompt", "alpha", "alpha", True, False, False, _NONE, id="repeat-same-slug-silent"),
    pytest.param("prompt", "beta", "alpha", True, False, False, InjectionDecision("bootstrap", "beta", "beta"), id="rebind-to-other-context"),
    pytest.param("prompt", "alpha", "alpha", True, False, True, InjectionDecision("bootstrap", "alpha", "alpha"), id="T-50-03-same-context-rebind"),
    pytest.param("prompt", "", "alpha", True, True, False, InjectionDecision("bootstrap", "alpha", "alpha"), id="compacted-recorded-slug-fallback"),
    pytest.param("prompt", "", "", False, False, False, InjectionDecision("preflight", "", ""), id="unbound-fresh-preflight"),
    pytest.param("prompt", "", "", True, False, False, _NONE, id="unbound-preflight-only-once"),
    pytest.param("prompt", "", "alpha", True, False, False, InjectionDecision("preflight", "alpha", ""), id="bind-lost-silently-after-five-idle-minutes-told-once"),
    pytest.param("prompt", "ghost", "", False, False, False, InjectionDecision("bootstrap", "ghost", "ghost"), id="S7-bound-without-specs-gets-its-next-step"),
    pytest.param("postcompact", "", "alpha", True, False, False, InjectionDecision("bootstrap", "alpha", None), id="postcompact-emits-never-stamps"),
    pytest.param("postcompact", "", "", False, False, False, InjectionDecision("preflight", "", None), id="postcompact-unbound-preflight-no-stamp"),
    pytest.param("session_restart", "", "alpha", True, False, False, InjectionDecision("bootstrap", "alpha", "alpha"), id="restart-re-emits-and-restamps"),
    pytest.param("session_restart", "", "", False, False, False, InjectionDecision("preflight", "", ""), id="restart-unbound-stamps-empty"),
    pytest.param("session_start", "alpha", "alpha", True, False, False, InjectionDecision("bootstrap", "alpha", "alpha"), id="AC1.2-a-new-session-is-never-a-repeat"),
    pytest.param("session_start", "", "alpha", True, True, False, InjectionDecision("preflight", "", ""), id="AC1.2-a-new-session-inherits-no-stamp"),
])
# fmt: on
def test_decide_injection(
    event: str, context: str, recorded: str, sentinel: bool, compacted: bool, rebound: bool, expected: InjectionDecision
) -> None:
    decision = decide_injection(
        event=event, context=context, recorded_slug=recorded, sentinel_exists=sentinel, compacted=compacted, rebound=rebound
    )
    assert decision == expected
