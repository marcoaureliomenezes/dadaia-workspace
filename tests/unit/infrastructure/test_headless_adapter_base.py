"""Single-source proof for the shared headless-adapter base (v0.1.30 Wave A).

The three real ``AgentRuntimePort`` adapters (``pi``/``codex``/``claude_sdk``)
once copy-pasted the security-relevant invariants ``_redact``/``_SECRET_NAME_PARTS``
and the git ``changed_paths`` override. After the de-duplication they all draw from
:mod:`dadaia_workspace.infrastructure.headless_adapter_base`. These tests FAIL if any
adapter's redaction or ``changed_paths`` behaviour diverges from the shared base —
the latent-security-bug guard the SPEC (A3) requires.

Behaviour is asserted three ways, strongest first:
* the bound symbols are the *same object* as the base (a re-defined copy fails);
* parametrized redaction parity across pi/codex/claude_sdk on the same input;
* parametrized ``changed_paths`` git-override parity across pi/codex.
Plus direct unit coverage of the base building blocks.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.infrastructure import (
    claude_sdk_runtime,
    codex_runtime,
    pi_runtime,
)
from dadaia_workspace.infrastructure.headless_adapter_base import (
    _SECRET_NAME_PARTS,
    ChangedPathsMixin,
    RedactionMixin,
    ResultMatch,
    SubprocessAdapterMixin,
    build_prompt_envelope,
    classify_result_payload,
    filter_env,
    normalize_artifact_refs,
)

#: A factory producing a freshly-constructed adapter that mixes in ``RedactionMixin``.
AdapterFactory = Callable[[], RedactionMixin]

#: A factory producing a CLI adapter that mixes in the full ``SubprocessAdapterMixin``
#: (carries the git ``changed_paths`` override + env filter).
CliAdapterFactory = Callable[[], SubprocessAdapterMixin]

# --------------------------------------------------------------------------- #
# Fakes                                                                        #
# --------------------------------------------------------------------------- #


class _FakeGit:
    """A ``_GitDiffPort`` returning a fixed diff regardless of path."""

    def __init__(self, changed: tuple[str, ...]) -> None:
        self._changed = changed
        self.calls: list[Path] = []

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        self.calls.append(path)
        return self._changed


def _request(runtime: AgentRuntimeKind) -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="do bounded work",
        runtime=runtime,
        context="dadaia-workspace",
        release_id="v0.1.30",
        allowed_paths=("repos/dadaia-workspace/**",),
        forbidden_paths=("secrets.py",),
    )


# --------------------------------------------------------------------------- #
# 1. Single-object identity — a re-defined copy in any adapter fails here.     #
# --------------------------------------------------------------------------- #


def test_shared_symbols_are_single_sourced_across_real_adapters() -> None:
    """All three real adapters bind their security-relevant mixins to the SAME
    shared base objects — a divergent re-defined copy on any adapter fails here.

    Covers: ``_redact`` (all three), ``_with_changed_paths`` (CLI pair), the
    ``_SECRET_NAME_PARTS`` constant (never locally redefined), and the env-filter
    / prompt-envelope surface (CLI pair).
    """
    assert pi_runtime.PiHeadlessAdapter._redact is RedactionMixin._redact
    assert codex_runtime.CodexExecAdapter._redact is RedactionMixin._redact
    assert claude_sdk_runtime.ClaudeSdkAdapter._redact is RedactionMixin._redact

    assert pi_runtime.PiHeadlessAdapter._with_changed_paths is ChangedPathsMixin._with_changed_paths
    assert (
        codex_runtime.CodexExecAdapter._with_changed_paths is ChangedPathsMixin._with_changed_paths
    )

    assert not hasattr(pi_runtime, "_SECRET_NAME_PARTS")
    assert not hasattr(codex_runtime, "_SECRET_NAME_PARTS")
    assert not hasattr(claude_sdk_runtime, "_SECRET_NAME_PARTS")
    # The single source still carries every secret token fragment.
    assert _SECRET_NAME_PARTS == ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")

    assert pi_runtime.PiHeadlessAdapter._env is SubprocessAdapterMixin._env
    assert codex_runtime.CodexExecAdapter._env is SubprocessAdapterMixin._env
    assert pi_runtime.PiHeadlessAdapter._prompt is SubprocessAdapterMixin._prompt
    assert codex_runtime.CodexExecAdapter._prompt is SubprocessAdapterMixin._prompt


# --------------------------------------------------------------------------- #
# 2. Redaction parity (behaviour) — same input → same output across adapters. #
# --------------------------------------------------------------------------- #


def _make_pi() -> pi_runtime.PiHeadlessAdapter:
    return pi_runtime.PiHeadlessAdapter(
        pi_runtime.PiHeadlessConfig(cwd=Path("/x")),
        environ={"ANTHROPIC_API_KEY": "sk-secret-123", "PATH": "/bin"},
    )


def _make_codex() -> codex_runtime.CodexExecAdapter:
    return codex_runtime.CodexExecAdapter(
        codex_runtime.CodexExecConfig(cwd=Path("/x")),
        environ={"ANTHROPIC_API_KEY": "sk-secret-123", "PATH": "/bin"},
    )


def _make_claude() -> claude_sdk_runtime.ClaudeSdkAdapter:
    return claude_sdk_runtime.ClaudeSdkAdapter(
        environ={"ANTHROPIC_API_KEY": "sk-secret-123", "PATH": "/bin"},
    )


@pytest.mark.parametrize(
    "make_adapter",
    [_make_pi, _make_codex, _make_claude],
    ids=["pi", "codex", "claude_sdk"],
)
def test_redaction_parity_across_all_three_adapters(make_adapter: AdapterFactory) -> None:
    """Every real adapter scrubs a secret-named env value identically (the
    falsifiable divergence test: if any adapter's redaction drifted from the
    shared base, its output for this input would differ), AND parity holds for
    every secret-name fragment family (TOKEN/KEY/SECRET/...) with an
    empty-valued secret-named key skipped, never redacted as a literal empty
    match."""
    adapter = make_adapter()
    text = "connection failed using token sk-secret-123 to PATH /bin"
    redacted = adapter._redact(text)
    assert "sk-secret-123" not in redacted
    assert "[REDACTED]" in redacted
    # PATH is not a secret-named var → its value must survive untouched.
    assert "/bin" in redacted
    # Identical scrub for every adapter (the single-source guarantee).
    assert redacted == "connection failed using token [REDACTED] to PATH /bin"

    adapter._environ = {
        "MY_TOKEN": "t-val",
        "API_KEY": "k-val",
        "DB_SECRET": "s-val",
        "USER_PASSWORD": "p-val",
        "AWS_CREDENTIAL": "c-val",
        "PUBLIC_VALUE": "ok",
        "EMPTY_SECRET": "",
    }
    out = adapter._redact("t-val k-val s-val p-val c-val ok")
    assert out == "[REDACTED] [REDACTED] [REDACTED] [REDACTED] [REDACTED] ok"


# --------------------------------------------------------------------------- #
# 3. changed_paths parity (behaviour) — git override identical for CLI pair.   #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "make_adapter",
    [_make_pi, _make_codex],
    ids=["pi", "codex"],
)
def test_changed_paths_override_parity_for_cli_adapters(
    make_adapter: CliAdapterFactory,
) -> None:
    """The git diff UNCONDITIONALLY overwrites a self-reported ``changed_paths``,
    and with no git client injected the result passes through untouched (parity
    for both branches, across both CLI adapters)."""
    adapter = make_adapter()
    adapter._git = _FakeGit(("a.py", "b.py"))
    lying = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        structured_output={"changed_paths": "i-only-touched-readme.md"},
    )
    out = adapter._with_changed_paths(lying)
    assert out.structured_output["changed_paths"] == "a.py,b.py"

    adapter._git = None
    result = AgentRunResult(status=AgentRunStatus.SUCCEEDED, summary="ok")
    assert adapter._with_changed_paths(result) is result


# --------------------------------------------------------------------------- #
# 4. Base building-block unit coverage.                                        #
# --------------------------------------------------------------------------- #


def test_filter_env_and_build_prompt_envelope() -> None:
    env = {"PATH": "/bin", "HOME": "/h", "DADAIA_PRIVATE": "leak"}
    out = filter_env(env, ("PATH", "HOME", "ANTHROPIC_API_KEY"))
    assert out == {"PATH": "/bin", "HOME": "/h"}
    assert filter_env({"DADAIA_PRIVATE": "leak"}, ("PATH", "HOME")) == {}

    import json

    request = _request(AgentRuntimeKind.PI_HEADLESS)
    payload = json.loads(build_prompt_envelope(request))
    assert set(payload) == {
        "role",
        "prompt",
        "context",
        "release_id",
        "task_id",
        "allowed_paths",
        "forbidden_paths",
        "expected_schema",
        "required_evidence",
    }
    assert payload["role"] == "software-engineer"
    assert payload["allowed_paths"] == ["repos/dadaia-workspace/**"]
    # Stable, sorted serialization (byte-for-byte reproducible).
    assert build_prompt_envelope(request) == build_prompt_envelope(request)


# ---------------------------------------------------------------------------
# normalize_artifact_refs / classify_result_payload — one shape-table param.
#
# Covers (v0.1.32 Wave C + FR2 T-66-05): plain string-list, richer object-list
# (was silently dropped pre-fix), mixed list with garbage ignored, absent/non-list
# → empty, singular artifact.path fallback (+ populated-list precedence, +
# missing-path stays empty), and schema_version as an equivalent STRICT label.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "expected_refs"),
    [
        pytest.param(
            {"artifact_refs": [".dadaia/handoff/dadaia-workspace/a.handoff.json"]},
            (".dadaia/handoff/dadaia-workspace/a.handoff.json",),
            id="plain-string-list",
        ),
        pytest.param(
            {
                "artifact_refs": [
                    {
                        "type": "handoff",
                        "path": ".dadaia/handoff/dadaia-workspace/spec.handoff.json",
                        "content_hash": "f95...",
                    }
                ]
            },
            (".dadaia/handoff/dadaia-workspace/spec.handoff.json",),
            id="object-list-with-path",
        ),
        pytest.param(
            {
                "artifact_refs": [
                    "string/ref.json",
                    {"path": "object/ref.json"},
                    {"no_path": "x"},  # dict without a path → ignored
                    123,  # non-str/dict → ignored
                    "",  # empty string → ignored
                ]
            },
            ("string/ref.json", "object/ref.json"),
            id="mixed-list-ignores-garbage",
        ),
        pytest.param({"artifact_refs": "not-a-list"}, (), id="non-list-is-empty"),
        pytest.param({}, (), id="absent-is-empty"),
        pytest.param(
            {"artifact": {"type": "other", "path": "repos/x/f.py"}},
            ("repos/x/f.py",),
            id="singular-artifact-path-fallback",
        ),
        pytest.param(
            {
                "artifact_refs": [".dadaia/handoff/dadaia-workspace/a.handoff.json"],
                "artifact": {"type": "other", "path": "repos/x/should-not-be-used.py"},
            },
            (".dadaia/handoff/dadaia-workspace/a.handoff.json",),
            id="populated-list-wins-over-singular-fallback",
        ),
        pytest.param(
            {"artifact": {"type": "other"}},
            (),
            id="singular-artifact-missing-path-stays-empty",
        ),
    ],
)
def test_normalize_artifact_refs_shape_table(
    payload: dict[str, object], expected_refs: tuple[str, ...]
) -> None:
    assert normalize_artifact_refs(payload) == expected_refs


def test_classify_result_payload_accepts_schema_version_as_strict_label() -> None:
    """AC2.1 — ``schema_version`` is an equivalent label to ``schema`` for STRICT.

    A real worker that labels the transport id under ``schema_version`` instead
    of ``schema`` genuinely IS the result object; it must classify STRICT, not
    fall through to the (narrower) structural check or NONE.
    """
    assert normalize_artifact_refs({"artifact": "not-a-dict"}) == ()

    payload: dict[str, object] = {
        "schema_version": "agent-run-result-v1",
        "status": "succeeded",
        "summary": "done",
        "artifact_refs": [],
    }
    assert classify_result_payload(payload, "agent-run-result-v1") is ResultMatch.STRICT
