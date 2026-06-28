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
    headless_adapter_base,
    pi_runtime,
)
from dadaia_workspace.infrastructure.headless_adapter_base import (
    _SECRET_NAME_PARTS,
    RedactionMixin,
    SubprocessAdapterMixin,
    build_prompt_envelope,
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


def test_redaction_is_single_sourced_across_real_adapters() -> None:
    """All three real adapters bind ``_redact`` to the shared ``RedactionMixin``.

    Each adapter resolves ``_redact`` through its MRO. A divergent re-defined
    ``_redact`` on any adapter would no longer be ``RedactionMixin._redact`` and
    this assertion would fail.
    """
    assert pi_runtime.PiHeadlessAdapter._redact is RedactionMixin._redact
    assert codex_runtime.CodexExecAdapter._redact is RedactionMixin._redact
    assert claude_sdk_runtime.ClaudeSdkAdapter._redact is RedactionMixin._redact


def test_changed_paths_override_is_single_sourced_for_cli_adapters() -> None:
    """The CLI adapters share one ``_with_changed_paths`` (the git Ring-2 override)."""
    from dadaia_workspace.infrastructure.headless_adapter_base import ChangedPathsMixin

    assert pi_runtime.PiHeadlessAdapter._with_changed_paths is ChangedPathsMixin._with_changed_paths
    assert (
        codex_runtime.CodexExecAdapter._with_changed_paths is ChangedPathsMixin._with_changed_paths
    )


def test_secret_name_parts_not_redefined_in_adapter_modules() -> None:
    """No real adapter module redefines its own ``_SECRET_NAME_PARTS`` constant.

    A local copy is exactly the divergence risk this de-duplication removes.
    """
    assert not hasattr(pi_runtime, "_SECRET_NAME_PARTS")
    assert not hasattr(codex_runtime, "_SECRET_NAME_PARTS")
    assert not hasattr(claude_sdk_runtime, "_SECRET_NAME_PARTS")
    # The single source still carries every secret token fragment.
    assert _SECRET_NAME_PARTS == ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")


def test_env_filter_and_prompt_envelope_are_single_sourced() -> None:
    """The CLI adapters share the env-filter and prompt-envelope surface."""
    assert pi_runtime.PiHeadlessAdapter._env is SubprocessAdapterMixin._env
    assert pi_runtime.PiHeadlessAdapter._prompt is SubprocessAdapterMixin._prompt
    assert codex_runtime.CodexExecAdapter._prompt is SubprocessAdapterMixin._prompt


def test_codex_env_extends_shared_filter_with_isolated_runtime_home(tmp_path: Path) -> None:
    """Codex keeps the shared env allowlist, then overlays isolated runtime dirs."""
    workspace = tmp_path / "workspace"
    (workspace / ".dadaia").mkdir(parents=True)
    (workspace / "repos").mkdir()
    adapter = codex_runtime.CodexExecAdapter(
        codex_runtime.CodexExecConfig(cwd=workspace),
        environ={
            "PATH": "/bin",
            "HOME": str(tmp_path / "host-home"),
            "OPENAI_API_KEY": "sk-secret",
        },
    )

    env = adapter._env()

    assert env["PATH"] == "/bin"
    assert "OPENAI_API_KEY" not in env
    assert env["HOME"] == str(workspace / ".dadaia" / "tmp" / "codex-runtime" / "home")
    assert env["CODEX_HOME"] == str(workspace / ".dadaia" / "tmp" / "codex-runtime" / "codex-home")


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
    """Every real adapter scrubs a secret-named env value identically.

    This is the falsifiable divergence test: if any adapter's redaction drifted
    from the shared base, its output for this input would differ.
    """
    adapter = make_adapter()
    text = "connection failed using token sk-secret-123 to PATH /bin"
    redacted = adapter._redact(text)
    assert "sk-secret-123" not in redacted
    assert "[REDACTED]" in redacted
    # PATH is not a secret-named var → its value must survive untouched.
    assert "/bin" in redacted
    # Identical scrub for every adapter (the single-source guarantee).
    assert redacted == "connection failed using token [REDACTED] to PATH /bin"


@pytest.mark.parametrize(
    "make_adapter",
    [_make_pi, _make_codex, _make_claude],
    ids=["pi", "codex", "claude_sdk"],
)
def test_no_secret_named_env_value_is_left_unredacted(make_adapter: AdapterFactory) -> None:
    """Parity for every secret-name fragment family (TOKEN/KEY/SECRET/...)."""
    adapter = make_adapter()
    adapter._environ = {
        "MY_TOKEN": "t-val",
        "API_KEY": "k-val",
        "DB_SECRET": "s-val",
        "USER_PASSWORD": "p-val",
        "AWS_CREDENTIAL": "c-val",
        "PUBLIC_VALUE": "ok",
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
    """The git diff UNCONDITIONALLY overwrites a self-reported ``changed_paths``."""
    adapter = make_adapter()
    adapter._git = _FakeGit(("a.py", "b.py"))
    lying = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        structured_output={"changed_paths": "i-only-touched-readme.md"},
    )
    out = adapter._with_changed_paths(lying)
    assert out.structured_output["changed_paths"] == "a.py,b.py"


@pytest.mark.parametrize(
    "make_adapter",
    [_make_pi, _make_codex],
    ids=["pi", "codex"],
)
def test_changed_paths_noop_without_git(make_adapter: CliAdapterFactory) -> None:
    """With no git client injected, the result is returned untouched (parity)."""
    adapter = make_adapter()
    adapter._git = None
    result = AgentRunResult(status=AgentRunStatus.SUCCEEDED, summary="ok")
    assert adapter._with_changed_paths(result) is result


# --------------------------------------------------------------------------- #
# 4. Base building-block unit coverage.                                        #
# --------------------------------------------------------------------------- #


def test_filter_env_keeps_only_present_allowlisted_keys() -> None:
    env = {"PATH": "/bin", "HOME": "/h", "DADAIA_PRIVATE": "leak"}
    out = filter_env(env, ("PATH", "HOME", "ANTHROPIC_API_KEY"))
    assert out == {"PATH": "/bin", "HOME": "/h"}


def test_filter_env_returns_empty_when_no_allowlisted_key_present() -> None:
    assert filter_env({"DADAIA_PRIVATE": "leak"}, ("PATH", "HOME")) == {}


def test_build_prompt_envelope_is_deterministic_and_carries_all_fields() -> None:
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


def test_redaction_mixin_skips_empty_values() -> None:
    class _Host(RedactionMixin):
        def __init__(self) -> None:
            self._environ = {"API_KEY": "", "DB_PASSWORD": "pw"}

    out = _Host()._redact("pw stays? no")
    assert out == "[REDACTED] stays? no"


def test_module_lives_in_infrastructure_layer() -> None:
    assert headless_adapter_base.__name__.startswith("dadaia_workspace.infrastructure")


# ---------------------------------------------------------------------------
# normalize_artifact_refs — accept BOTH real-worker shapes (v0.1.32 Wave C)
# ---------------------------------------------------------------------------


def test_normalize_artifact_refs_accepts_plain_string_list() -> None:
    """The string-list shape a real worker emitted for release_scope."""
    payload = {"artifact_refs": [".dadaia/handoff/dadaia-workspace/a.handoff.json"]}
    assert normalize_artifact_refs(payload) == (".dadaia/handoff/dadaia-workspace/a.handoff.json",)


def test_normalize_artifact_refs_accepts_object_list_with_path() -> None:
    """The richer object shape a real worker emitted for spec_create — was silently dropped.

    Before this, only ``str`` items were kept, so the object form yielded empty refs and a
    real review/create step BLOCKed on "missing artifact evidence" (live e2e, v0.1.32).
    """
    payload = {
        "artifact_refs": [
            {
                "type": "handoff",
                "path": ".dadaia/handoff/dadaia-workspace/spec.handoff.json",
                "content_hash": "f95...",
            }
        ]
    }
    assert normalize_artifact_refs(payload) == (
        ".dadaia/handoff/dadaia-workspace/spec.handoff.json",
    )


def test_normalize_artifact_refs_mixed_and_ignores_garbage() -> None:
    payload = {
        "artifact_refs": [
            "string/ref.json",
            {"path": "object/ref.json"},
            {"no_path": "x"},  # dict without a path → ignored
            123,  # non-str/dict → ignored
            "",  # empty string → ignored
        ]
    }
    assert normalize_artifact_refs(payload) == ("string/ref.json", "object/ref.json")


def test_normalize_artifact_refs_non_list_or_absent_is_empty() -> None:
    assert normalize_artifact_refs({"artifact_refs": "not-a-list"}) == ()
    assert normalize_artifact_refs({}) == ()
